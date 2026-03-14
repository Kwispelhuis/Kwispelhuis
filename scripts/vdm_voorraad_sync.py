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

FTP_HOST    = os.environ.get("VDM_FTP_HOST", "ftp.vdmdtg.nl")
FTP_USER    = os.environ.get("VDM_FTP_USER", "HondenHappiness")
FTP_PASS    = os.environ.get("VDM_FTP_PASS", "OLgH29N2B8JqWln9")
FTP_BESTAND = "/Voorraad/voorraadv4.xml"

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN", "xjwcui-7s.myshopify.com")
CLIENT_ID      = os.environ.get("SHOPIFY_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("SHOPIFY_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

def haal_access_token():
    r = requests.post(
        f"https://{SHOPIFY_DOMAIN}/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"},
        headers={"Content-Type": "application/json"}
    )
    if r.status_code == 200:
        return r.json().get("access_token")
    raise Exception(f"Token ophalen mislukt: {r.status_code} {r.text}")

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
    for tag in ['Product', 'Artikel', 'artikel', 'product']:
        items = root.findall(f'.//{tag}')
        if items:
            for item in items:
                arintnum = (item.findtext('ARINTNUM') or '').strip()
                vrd = int(item.findtext('VRD_CNS_EENHEID') or item.findtext('VOORRAAD_CNS_EENHEID') or 0)
                status = item.findtext('STATUS') or '1'
                if arintnum:
                    voorraad[arintnum] = 0 if status == '9' else vrd
            break
    log.info(f"Voorraad geparsed: {len(voorraad)} artikelen")
    return voorraad

def main():
    start = datetime.now()
    log.info("=" * 50)
    log.info(f"Voorraad sync gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    token = haal_access_token()
    HEADERS = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"

    buf = download_voorraad()
    vdm_voorraad = parse_voorraad(buf)

    # Locatie ophalen
    locaties = requests.get(f"{BASE}/locations.json", headers=HEADERS).json().get('locations', [])
    locatie_id = locaties[0]['id']
    log.info(f"Locatie: {locatie_id}")

    # SKU → inventory_item_id
    sku_map = {}
    url = f"{BASE}/variants.json?limit=250&fields=sku,inventory_item_id"
    while url:
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 429:
            log.warning("Rate limit, wacht 15s...")
            time.sleep(15)
            continue
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
    log.info(f"  {len(sku_map)} inventory items geladen")

    # Voorraad updaten
    succesvol = overgeslagen = 0
    for sku, inv_item_id in sku_map.items():
        if sku not in vdm_voorraad:
            overgeslagen += 1
            continue
        r = requests.post(f"{BASE}/inventory_levels/set.json", headers=HEADERS,
                          json={"location_id": locatie_id, "inventory_item_id": inv_item_id,
                                "available": vdm_voorraad[sku]})
        if r.status_code == 200:
            succesvol += 1
        else:
            log.warning(f"Fout {sku}: {r.status_code}")
        time.sleep(0.4)

    duur = (datetime.now() - start).seconds
    log.info(f"Klaar in {duur}s — Succesvol: {succesvol}, Overgeslagen: {overgeslagen}")

if __name__ == "__main__":
    main()
