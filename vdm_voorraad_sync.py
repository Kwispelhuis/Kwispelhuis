#!/usr/bin/env python3
"""
VDM Voorraad Sync → Shopify
Draait elke 15 minuten via GitHub Actions
"""

import ftplib
import xml.etree.ElementTree as ET
import requests
import time
import logging
import os
from io import BytesIO
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
FTP_HOST  = os.environ.get("VDM_FTP_HOST", "ftp.vdmdtg.nl")
FTP_USER  = os.environ.get("VDM_FTP_USER", "HondenHappiness")
FTP_PASS  = os.environ.get("VDM_FTP_PASS", "OLgH29N2B8JqWln9")
FTP_BESTAND = "/Voorraad/voorraadv4.xml"

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "xjwcui-7s.myshopify.com")
SHOPIFY_TOKEN  = os.environ.get("SHOPIFY_TOKEN")

SHOPIFY_BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"
HEADERS = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def download_voorraad():
    log.info("FTP: voorraadv4.xml downloaden...")
    buf = BytesIO()
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.retrbinary(f"RETR {FTP_BESTAND}", buf.write)
    buf.seek(0)
    return buf

def parse_voorraad(buf):
    tree = ET.parse(buf)
    root = tree.getroot()
    voorraad = {}
    # Probeer beide mogelijke tag-namen
    for tag in ['Product', 'Artikel', 'artikel', 'product']:
        items = root.findall(f'.//{tag}')
        if items:
            for item in items:
                arintnum = (item.findtext('ARINTNUM') or
                           item.findtext('arintnum') or '').strip()
                vrd = int(item.findtext('VRD_CNS_EENHEID') or
                         item.findtext('VOORRAAD_CNS_EENHEID') or 0)
                status = item.findtext('STATUS') or '1'
                if arintnum:
                    voorraad[arintnum] = 0 if status == '9' else vrd
            break
    log.info(f"Voorraad geparsed: {len(voorraad)} artikelen")
    return voorraad

def haal_locatie():
    r = requests.get(f"{SHOPIFY_BASE}/locations.json", headers=HEADERS)
    r.raise_for_status()
    locaties = r.json().get('locations', [])
    locatie_id = locaties[0]['id']
    log.info(f"Locatie: {locatie_id} ({locaties[0]['name']})")
    return locatie_id

def haal_inventory_items():
    """SKU → inventory_item_id mapping"""
    log.info("Shopify inventory items ophalen...")
    sku_map = {}
    url = f"{SHOPIFY_BASE}/variants.json?limit=250&fields=sku,inventory_item_id"
    while url:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        for v in r.json().get('variants', []):
            if v.get('sku'):
                sku_map[v['sku']] = v['inventory_item_id']
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.strip().split(';')[0].strip('<> ')
        time.sleep(0.3)
    log.info(f"  {len(sku_map)} items geladen")
    return sku_map

def sync_voorraad(locatie_id, vdm_voorraad, sku_map):
    succesvol = 0
    overgeslagen = 0

    for sku, inv_item_id in sku_map.items():
        if sku not in vdm_voorraad:
            overgeslagen += 1
            continue

        nieuwe_voorraad = vdm_voorraad[sku]
        r = requests.post(
            f"{SHOPIFY_BASE}/inventory_levels/set.json",
            headers=HEADERS,
            json={
                "location_id": locatie_id,
                "inventory_item_id": inv_item_id,
                "available": nieuwe_voorraad
            }
        )
        if r.status_code == 200:
            succesvol += 1
        else:
            log.warning(f"Fout {sku}: {r.status_code} {r.text[:100]}")

        time.sleep(0.4)

    return succesvol, overgeslagen

def main():
    start = datetime.now()
    log.info("=" * 50)
    log.info(f"Voorraad sync gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    buf = download_voorraad()
    vdm_voorraad = parse_voorraad(buf)
    locatie_id = haal_locatie()
    sku_map = haal_inventory_items()

    succesvol, overgeslagen = sync_voorraad(locatie_id, vdm_voorraad, sku_map)

    duur = (datetime.now() - start).seconds
    log.info(f"Klaar in {duur}s — Succesvol: {succesvol}, Overgeslagen: {overgeslagen}")

if __name__ == "__main__":
    main()
