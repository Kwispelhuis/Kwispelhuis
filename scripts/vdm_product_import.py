#!/usr/bin/env python3
"""
VDM Product Import → Shopify
Draait dagelijks om 8:00 via GitHub Actions
"""

import ftplib
import xml.etree.ElementTree as ET
import requests
import time
import logging
import os
import re
from io import BytesIO
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
FTP_HOST    = os.environ.get("VDM_FTP_HOST", "ftp.vdmdtg.nl")
FTP_USER    = os.environ.get("VDM_FTP_USER", "HondenHappiness")
FTP_PASS    = os.environ.get("VDM_FTP_PASS", "OLgH29N2B8JqWln9")
FTP_BESTAND = "/export/exportXML_UTF8.xml"

SHOPIFY_DOMAIN    = os.environ.get("SHOPIFY_DOMAIN", "xjwcui-7s.myshopify.com")
CLIENT_ID         = os.environ.get("SHOPIFY_CLIENT_ID")
CLIENT_SECRET     = os.environ.get("SHOPIFY_CLIENT_SECRET")
FOTO_BASE         = os.environ.get("FOTO_BASE", "https://fotos.kwispelhuis.nl")

ALLEEN_HOOFDGROEP = "HOND"
EXCLUDE_DIEPVRIES = True

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def haal_access_token():
    """Haal access token op via client credentials"""
    log.info("Shopify access token ophalen...")
    r = requests.post(
        f"https://{SHOPIFY_DOMAIN}/admin/oauth/access_token",
        json={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        },
        headers={"Content-Type": "application/json"}
    )
    if r.status_code == 200:
        token = r.json().get("access_token")
        log.info("Token opgehaald")
        return token
    else:
        raise Exception(f"Token ophalen mislukt: {r.status_code} {r.text}")

def download_xml(token):
    log.info("FTP: exportXML_UTF8.xml downloaden...")
    buf = BytesIO()
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.retrbinary(f"RETR {FTP_BESTAND}", buf.write)
    buf.seek(0)
    log.info("Download klaar")
    return buf

def maak_handle(basis, sub, arintnum):
    tekst = f"{basis} {sub}".lower()
    tekst = re.sub(r'[^a-z0-9\s]', '', tekst)
    tekst = re.sub(r'\s+', '-', tekst.strip())
    return f"{tekst[:80]}-{arintnum}"

def verwerk_product(p):
    arintnum   = p.findtext('ARINTNUM') or ''
    basis      = p.findtext('BASIS_OMS') or ''
    sub        = p.findtext('SUB_OMS') or ''
    merk       = p.findtext('MERK') or ''
    subgroep   = p.findtext('SUBGROEP') or ''
    ean        = p.findtext('EAN') or ''
    gewicht    = int(p.findtext('GEWICHT') or 0)
    voorraad   = int(p.findtext('VOORRAAD_CNS_EENHEID') or 0)
    prijs      = float(p.findtext('ADVIESPRIJS_INC_STUK') or 0)
    cost       = float(p.findtext('UWPRIJS_EXC') or 0)
    beschr     = p.findtext('ARTIKEL_CONTENT_HTML') or ''
    op_best    = p.findtext('OPBESTELLING') == '1'
    verzend    = p.findtext('VERZENDWIJZE') or ''

    titel = f"{basis.strip()} {sub.strip()}".strip().title()
    tags = []
    if merk: tags.append(f"merk-{merk.lower().replace(' ', '-')}")
    if subgroep: tags.append(subgroep.lower().replace(' ', '-'))
    if op_best: tags.append("op-bestelling")
    if verzend == 'diepvries': tags.append("diepvries")

    return {
        "handle": maak_handle(basis, sub, arintnum),
        "title": titel,
        "body_html": beschr.strip() or f"{titel} van {merk}.",
        "vendor": merk.title() or "Onbekend",
        "product_type": subgroep.title(),
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
        "images": [{"src": f"{FOTO_BASE}/bigfotos/{arintnum}.jpg", "alt": titel}],
        "metafields": [
            {"namespace": "custom", "key": "vdm_id", "value": arintnum, "type": "single_line_text_field"},
            {"namespace": "custom", "key": "ean", "value": ean, "type": "single_line_text_field"},
            {"namespace": "custom", "key": "verzendwijze", "value": verzend, "type": "single_line_text_field"},
        ]
    }

def haal_bestaande_skus(headers, base):
    log.info("Bestaande Shopify SKUs ophalen...")
    skus = {}
    url = f"{base}/variants.json?limit=250&fields=id,sku,product_id,inventory_item_id"
    while url:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        for v in r.json().get('variants', []):
            if v.get('sku'):
                skus[v['sku']] = {'product_id': v['product_id'], 'inventory_item_id': v['inventory_item_id']}
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip('<> ')
        time.sleep(0.5)
    log.info(f"  {len(skus)} bestaande SKUs gevonden")
    return skus

def main():
    start = datetime.now()
    log.info("=" * 60)
    log.info(f"Product import gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    token = haal_access_token()
    HEADERS = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"

    buf = download_xml(token)
    tree = ET.parse(buf)
    root = tree.getroot()
    alle = root.findall('Product')
    log.info(f"Totaal in XML: {len(alle)} producten")

    gefilterd = [p for p in alle
                 if (not ALLEEN_HOOFDGROEP or p.findtext('HOOFDGROEP') == ALLEEN_HOOFDGROEP)
                 and not (EXCLUDE_DIEPVRIES and p.findtext('VERZENDWIJZE') == 'diepvries')]
    log.info(f"Na filter: {len(gefilterd)} producten")

    bestaande = haal_bestaande_skus(HEADERS, BASE)

    nieuw = bijgewerkt = fouten = 0

    for p in gefilterd:
        arintnum = p.findtext('ARINTNUM')
        data = verwerk_product(p)

        if arintnum in bestaande:
            product_id = bestaande[arintnum]['product_id']
            r = requests.put(f"{BASE}/products/{product_id}.json",
                             headers=HEADERS,
                             json={"product": {"id": product_id, "vendor": data["vendor"],
                                               "product_type": data["product_type"], "tags": data["tags"]}})
            if r.status_code == 200:
                bijgewerkt += 1
            else:
                fouten += 1
        else:
            r = requests.post(f"{BASE}/products.json", headers=HEADERS, json={"product": data})
            if r.status_code == 201:
                nieuw += 1
            else:
                log.warning(f"Fout {arintnum}: {r.status_code} {r.text[:100]}")
                fouten += 1

        time.sleep(0.5)

    duur = (datetime.now() - start).seconds
    log.info(f"Klaar in {duur}s — Nieuw: {nieuw}, Bijgewerkt: {bijgewerkt}, Fouten: {fouten}")

if __name__ == "__main__":
    main()
