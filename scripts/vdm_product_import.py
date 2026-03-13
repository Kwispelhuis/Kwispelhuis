#!/usr/bin/env python3
"""
VDM Product Import → Shopify
- Nieuwe producten: alles invullen inclusief type/tags via mapping + foto via FTP
- Bestaande producten: alleen prijs + foto updaten als die ontbreekt
- Foto's worden per batch van 100 via FTP gedownload en als base64 naar Shopify gestuurd
"""

import ftplib
import xml.etree.ElementTree as ET
import requests
import time
import logging
import os
import re
import sys
import base64
from io import BytesIO
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from vdm_mapping import get_mapping

FTP_HOST    = os.environ.get("VDM_FTP_HOST", "ftp.vdmdtg.nl")
FTP_USER    = os.environ.get("VDM_FTP_USER", "HondenHappiness")
FTP_PASS    = os.environ.get("VDM_FTP_PASS", "OLgH29N2B8JqWln9")
FTP_BESTAND = "/export/exportXML_UTF8.xml"
FTP_FOTOS   = "/fotos"

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "xjwcui-7s.myshopify.com")
CLIENT_ID      = os.environ.get("SHOPIFY_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("SHOPIFY_CLIENT_SECRET")

ALLEEN_HOOFDGROEP = "HOND"
EXCLUDE_DIEPVRIES = True
FOTO_BATCH_SIZE   = 100

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)


def haal_access_token():
    r = requests.post(
        f"https://{SHOPIFY_DOMAIN}/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"},
        headers={"Content-Type": "application/json"}
    )
    if r.status_code == 200:
        log.info("Token opgehaald")
        return r.json().get("access_token")
    raise Exception(f"Token ophalen mislukt: {r.status_code} {r.text}")


def download_xml():
    log.info("FTP: exportXML_UTF8.xml downloaden...")
    buf = BytesIO()
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.retrbinary(f"RETR {FTP_BESTAND}", buf.write)
    buf.seek(0)
    log.info("Download klaar")
    return buf


def download_fotos_batch(arintnums):
    """Download een batch fotos van FTP, geeft dict {arintnum: base64_string} terug."""
    fotos = {}
    try:
        with ftplib.FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            for arintnum in arintnums:
                buf = BytesIO()
                try:
                    ftp.retrbinary(f"RETR {FTP_FOTOS}/{arintnum}.jpg", buf.write)
                    buf.seek(0)
                    data = buf.read()
                    if len(data) > 0:
                        fotos[arintnum] = base64.b64encode(data).decode('utf-8')
                except ftplib.error_perm:
                    pass  # Foto bestaat niet voor dit artikel
    except Exception as e:
        log.warning(f"FTP foto batch fout: {e}")
    return fotos


def maak_handle(basis, sub, arintnum):
    tekst = f"{basis} {sub}".lower()
    tekst = re.sub(r'[^a-z0-9\s]', '', tekst)
    tekst = re.sub(r'\s+', '-', tekst.strip())
    return f"{tekst[:80]}-{arintnum}"


def haal_bestaande_producten(headers, base):
    log.info("Bestaande Shopify producten ophalen...")
    producten = {}
    prod_info = {}

    log.info("Product info + foto-status ophalen...")
    url = f"{base}/products.json?limit=250&fields=id,tags,product_type,images"
    while url:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        for p in r.json().get('products', []):
            prod_info[p['id']] = {
                'tags': p.get('tags', ''),
                'product_type': p.get('product_type', ''),
                'heeft_foto': len(p.get('images', [])) > 0
            }
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip('<> ')
        time.sleep(0.3)

    url = f"{base}/variants.json?limit=250&fields=id,sku,product_id,inventory_item_id,price"
    while url:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        for v in r.json().get('variants', []):
            if v.get('sku'):
                pid = v['product_id']
                info = prod_info.get(pid, {})
                producten[v['sku']] = {
                    'product_id': pid,
                    'variant_id': v['id'],
                    'inventory_item_id': v['inventory_item_id'],
                    'prijs': v.get('price'),
                    'heeft_foto': info.get('heeft_foto', False),
                    'tags': info.get('tags', ''),
                    'product_type': info.get('product_type', '')
                }
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip('<> ')
        time.sleep(0.3)

    log.info(f"  {len(producten)} bestaande producten gevonden")
    return producten


def upload_foto(headers, base, product_id, arintnum, titel, foto_b64):
    # Check bestandsgrootte (max 15MB als base64)
    if len(foto_b64) > 20_000_000:
        log.warning(f"Foto {arintnum} te groot ({len(foto_b64)} bytes), overgeslagen")
        return False
    for poging in range(3):
        r = requests.post(
            f"{base}/products/{product_id}/images.json",
            headers=headers,
            json={"image": {
                "attachment": foto_b64,
                "filename": f"{arintnum}.jpg",
                "alt": titel
            }}
        )
        if r.status_code in (200, 201):
            return True
        if r.status_code == 429:
            log.warning(f"Rate limit foto {arintnum}, wacht 10s...")
            time.sleep(10)
        else:
            log.warning(f"Foto upload fout {arintnum}: {r.status_code} {r.text[:80]}")
            return False
    return False


def main():
    start = datetime.now()
    log.info("=" * 60)
    log.info(f"Product import gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    token = haal_access_token()
    HEADERS = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"

    buf = download_xml()
    tree = ET.parse(buf)
    root = tree.getroot()
    alle = root.findall('Product')
    log.info(f"Totaal in XML: {len(alle)} producten")

    gefilterd = [p for p in alle
                 if (not ALLEEN_HOOFDGROEP or p.findtext('HOOFDGROEP') == ALLEEN_HOOFDGROEP)
                 and not (EXCLUDE_DIEPVRIES and p.findtext('VERZENDWIJZE') == 'diepvries')]
    log.info(f"Na filter: {len(gefilterd)} producten")

    bestaande = haal_bestaande_producten(HEADERS, BASE)

    nieuw = prijs_updates = foto_updates = fouten = 0
    totaal_batches = (len(gefilterd) + FOTO_BATCH_SIZE - 1) // FOTO_BATCH_SIZE

    for batch_start in range(0, len(gefilterd), FOTO_BATCH_SIZE):
        batch = gefilterd[batch_start:batch_start + FOTO_BATCH_SIZE]
        batch_num = batch_start // FOTO_BATCH_SIZE + 1
        log.info(f"Batch {batch_num}/{totaal_batches} ({batch_start+1}-{min(batch_start+FOTO_BATCH_SIZE, len(gefilterd))})")

        # Bepaal welke artikelnummers een foto nodig hebben
        arintnums_voor_foto = []
        for p in batch:
            arintnum = p.findtext('ARINTNUM') or ''
            if not arintnum:
                continue
            if arintnum in bestaande:
                if not bestaande[arintnum]['heeft_foto']:
                    arintnums_voor_foto.append(arintnum)
            else:
                arintnums_voor_foto.append(arintnum)

        # Download foto's voor deze batch in één FTP sessie
        fotos = {}
        if arintnums_voor_foto:
            log.info(f"  {len(arintnums_voor_foto)} fotos downloaden van FTP...")
            fotos = download_fotos_batch(arintnums_voor_foto)
            log.info(f"  {len(fotos)} fotos gedownload")

        for p in batch:
            arintnum = p.findtext('ARINTNUM') or ''
            basis    = p.findtext('BASIS_OMS') or ''
            sub      = p.findtext('SUB_OMS') or ''
            merk     = p.findtext('MERK') or ''
            subgroep = p.findtext('SUBGROEP') or ''
            ean      = p.findtext('EAN') or ''
            gewicht  = int(p.findtext('GEWICHT') or 0)
            prijs    = float(p.findtext('ADVIESPRIJS_INC_STUK') or 0)
            cost     = float(p.findtext('UWPRIJS_EXC') or 0)
            beschr   = p.findtext('ARTIKEL_CONTENT_HTML') or ''
            op_best  = p.findtext('OPBESTELLING') == '1'
            verzend  = p.findtext('VERZENDWIJZE') or ''
            titel    = f"{basis.strip()} {sub.strip()}".strip().title()

            mapping      = get_mapping(subgroep, titel)
            product_type = mapping["type"]
            tags         = list(mapping["tags"])
            if merk: tags.append(f"merk-{merk.lower().replace(' ', '-')}")
            if op_best: tags.append("op-bestelling")

            foto_b64 = fotos.get(arintnum)

            if arintnum in bestaande:
                bestaand   = bestaande[arintnum]
                product_id = bestaand['product_id']
                variant_id = bestaand['variant_id']

                # Prijs updaten als gewijzigd
                nieuwe_prijs = str(round(prijs, 2))
                if bestaand['prijs'] != nieuwe_prijs:
                    for poging in range(3):
                        r = requests.put(f"{BASE}/variants/{variant_id}.json",
                                         headers=HEADERS,
                                         json={"variant": {"id": variant_id, "price": nieuwe_prijs,
                                                           "cost": str(round(cost, 2))}})
                        if r.status_code == 200:
                            prijs_updates += 1
                            break
                        elif r.status_code == 429:
                            log.warning(f"Rate limit prijs {arintnum}, wacht 10s...")
                            time.sleep(10)
                        else:
                            log.warning(f"Prijs update fout {arintnum}: {r.status_code}")
                            fouten += 1
                            break
                    time.sleep(0.5)

                # Tags samenvoegen: bestaande tags behouden + onze tags toevoegen
                bestaande_tags = set(t.strip() for t in bestaand['tags'].split(',') if t.strip())
                onze_tags = set(tags)
                if not onze_tags.issubset(bestaande_tags):
                    alle_tags = bestaande_tags | onze_tags
                    update = {}
                    update['tags'] = ', '.join(sorted(alle_tags))
                else:
                    update = {}
                if bestaand['product_type'] != product_type:
                    update['product_type'] = product_type
                if update:
                    r = requests.put(f"{BASE}/products/{product_id}.json",
                                     headers=HEADERS,
                                     json={"product": update})
                    if r.status_code != 200:
                        log.warning(f"Tags/type update fout {arintnum}: {r.status_code}")
                    time.sleep(0.3)

                # Foto uploaden als die ontbreekt
                if not bestaand['heeft_foto'] and foto_b64:
                    if upload_foto(HEADERS, BASE, product_id, arintnum, titel, foto_b64):
                        foto_updates += 1
                    else:
                        log.warning(f"Foto upload fout {arintnum}")
                        fouten += 1
                    time.sleep(0.3)

            else:
                # Nieuw product
                product_data = {
                    "handle": maak_handle(basis, sub, arintnum),
                    "title": titel,
                    "body_html": beschr.strip() or f"{titel} van {merk}.",
                    "vendor": merk.title() or "Onbekend",
                    "product_type": product_type,
                    "tags": ", ".join(tags),
                    "status": "active",
                    "variants": [{
                        "sku": arintnum,
                        "price": str(round(prijs, 2)),
                        "cost": str(round(cost, 2)),
                        "grams": gewicht,
                        "inventory_management": "shopify",
                        "inventory_policy": "deny",
                        "fulfillment_service": "manual",
                        "taxable": True,
                        "barcode": ean,
                        "weight": round(gewicht / 1000, 3),
                        "weight_unit": "kg",
                    }],
                    "metafields": [
                        {"namespace": "custom", "key": "vdm_id", "value": arintnum, "type": "single_line_text_field"},
                        {"namespace": "custom", "key": "ean", "value": ean, "type": "single_line_text_field"},
                        {"namespace": "custom", "key": "verzendwijze", "value": verzend, "type": "single_line_text_field"},
                    ]
                }

                if foto_b64:
                    product_data["images"] = [{"attachment": foto_b64, "filename": f"{arintnum}.jpg", "alt": titel}]

                r = requests.post(f"{BASE}/products.json", headers=HEADERS, json={"product": product_data})
                if r.status_code == 201:
                    nieuw += 1
                else:
                    log.warning(f"Nieuw product fout {arintnum}: {r.status_code} {r.text[:100]}")
                    fouten += 1

            time.sleep(0.5)

        log.info(f"  Batch {batch_num} klaar — Nieuw: {nieuw}, Prijs: {prijs_updates}, Fotos: {foto_updates}, Fouten: {fouten}")

    duur = (datetime.now() - start).seconds
    log.info("=" * 60)
    log.info(f"Klaar in {duur}s — Nieuw: {nieuw}, Prijs updates: {prijs_updates}, Foto updates: {foto_updates}, Fouten: {fouten}")


if __name__ == "__main__":
    main()
