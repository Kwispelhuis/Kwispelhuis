#!/usr/bin/env python3
"""
VDM Product Import → Shopify
Draait dagelijks om 8:00 via GitHub Actions
"""

import ftplib
import xml.etree.ElementTree as ET
import requests
import json
import time
import logging
import os
import html
import re
from io import BytesIO
from datetime import datetime

# ─── CONFIG (via environment variables) ──────────────────────────────────────
FTP_HOST     = os.environ.get("VDM_FTP_HOST", "ftp.vdmdtg.nl")
FTP_USER     = os.environ.get("VDM_FTP_USER", "HondenHappiness")
FTP_PASS     = os.environ.get("VDM_FTP_PASS", "OLgH29N2B8JqWln9")
FTP_BESTAND  = "/export/exportXML_UTF8.xml"

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "xjwcui-7s.myshopify.com")
SHOPIFY_TOKEN  = os.environ.get("SHOPIFY_TOKEN")
FOTO_BASE      = os.environ.get("FOTO_BASE", "https://fotos.kwispelhuis.nl")

SHOPIFY_BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"
HEADERS = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# ─── FILTERS ─────────────────────────────────────────────────────────────────
ALLEEN_HOOFDGROEP = "HOND"
EXCLUDE_DIEPVRIES = True

def download_xml():
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
    arintnum  = p.findtext('ARINTNUM') or ''
    basis     = p.findtext('BASIS_OMS') or ''
    sub       = p.findtext('SUB_OMS') or ''
    merk      = p.findtext('MERK') or ''
    subgroep  = p.findtext('SUBGROEP') or ''
    hoofdgroep= p.findtext('HOOFDGROEP') or ''
    ean       = p.findtext('EAN') or ''
    gewicht   = int(p.findtext('GEWICHT') or 0)
    voorraad  = int(p.findtext('VOORRAAD_CNS_EENHEID') or 0)
    prijs     = float(p.findtext('ADVIESPRIJS_INC_STUK') or 0)
    cost      = float(p.findtext('UWPRIJS_EXC') or 0)
    beschr    = p.findtext('ARTIKEL_CONTENT_HTML') or ''
    op_best   = p.findtext('OPBESTELLING') == '1'
    verzend   = p.findtext('VERZENDWIJZE') or ''

    titel = f"{basis.strip()} {sub.strip()}".strip().title()
    handle = maak_handle(basis, sub, arintnum)
    foto = f"{FOTO_BASE}/bigfotos/{arintnum}.jpg"

    tags = []
    if merk: tags.append(f"merk-{merk.lower().replace(' ', '-')}")
    if subgroep: tags.append(subgroep.lower().replace(' ', '-'))
    if op_best: tags.append("op-bestelling")
    if verzend == 'diepvries': tags.append("diepvries")

    return {
        "handle": handle,
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
        "images": [{"src": foto, "alt": titel}],
        "metafields": [
            {"namespace": "custom", "key": "vdm_id", "value": arintnum, "type": "single_line_text_field"},
            {"namespace": "custom", "key": "ean", "value": ean, "type": "single_line_text_field"},
            {"namespace": "custom", "key": "verzendwijze", "value": verzend, "type": "single_line_text_field"},
        ]
    }

def haal_bestaande_skus():
    """Haal alle bestaande SKUs op uit Shopify"""
    log.info("Bestaande Shopify SKUs ophalen...")
    skus = {}
    url = f"{SHOPIFY_BASE}/variants.json?limit=250&fields=id,sku,product_id,inventory_item_id"
    while url:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        for v in r.json().get('variants', []):
            if v.get('sku'):
                skus[v['sku']] = {
                    'variant_id': v['id'],
                    'product_id': v['product_id'],
                    'inventory_item_id': v['inventory_item_id']
                }
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip('<> ')
        time.sleep(0.5)
    log.info(f"  {len(skus)} bestaande SKUs gevonden")
    return skus

def maak_product_aan(product_data):
    r = requests.post(f"{SHOPIFY_BASE}/products.json",
                      headers=HEADERS,
                      json={"product": product_data})
    if r.status_code == 201:
        return r.json()['product']['id']
    else:
        log.warning(f"Fout aanmaken {product_data['variants'][0]['sku']}: {r.status_code} {r.text[:150]}")
        return None

def update_product(product_id, product_data):
    # Update alleen basis velden, niet title/description (SEO aanpassingen bewaren)
    update = {
        "id": product_id,
        "vendor": product_data["vendor"],
        "product_type": product_data["product_type"],
        "tags": product_data["tags"],
    }
    r = requests.put(f"{SHOPIFY_BASE}/products/{product_id}.json",
                     headers=HEADERS,
                     json={"product": update})
    return r.status_code == 200

def main():
    start = datetime.now()
    log.info("=" * 60)
    log.info(f"Product import gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    # Download en parse XML
    buf = download_xml()
    tree = ET.parse(buf)
    root = tree.getroot()
    alle = root.findall('Product')
    log.info(f"Totaal in XML: {len(alle)} producten")

    # Filter
    gefilterd = []
    for p in alle:
        if ALLEEN_HOOFDGROEP and p.findtext('HOOFDGROEP') != ALLEEN_HOOFDGROEP:
            continue
        if EXCLUDE_DIEPVRIES and p.findtext('VERZENDWIJZE') == 'diepvries':
            continue
        gefilterd.append(p)
    log.info(f"Na filter ({ALLEEN_HOOFDGROEP}, geen diepvries): {len(gefilterd)} producten")

    # Bestaande SKUs ophalen
    bestaande = haal_bestaande_skus()

    nieuw = 0
    bijgewerkt = 0
    fouten = 0

    for p in gefilterd:
        arintnum = p.findtext('ARINTNUM')
        product_data = verwerk_product(p)

        if arintnum in bestaande:
            # Bestaand product — update alleen niet-SEO velden
            product_id = bestaande[arintnum]['product_id']
            if update_product(product_id, product_data):
                bijgewerkt += 1
            else:
                fouten += 1
        else:
            # Nieuw product aanmaken
            pid = maak_product_aan(product_data)
            if pid:
                nieuw += 1
            else:
                fouten += 1

        time.sleep(0.5)  # rate limit

    duur = (datetime.now() - start).seconds
    log.info(f"Klaar in {duur}s — Nieuw: {nieuw}, Bijgewerkt: {bijgewerkt}, Fouten: {fouten}")

if __name__ == "__main__":
    main()
