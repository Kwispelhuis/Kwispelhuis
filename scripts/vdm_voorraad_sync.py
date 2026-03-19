#!/usr/bin/env python3
"""
VDM Voorraad Sync → Shopify
Draait elke 15 minuten via GitHub Actions
Alleen gewijzigde SKUs worden geüpdatet (delta sync)
"""

import ftplib
import xml.etree.ElementTree as ET
import requests
import time
import logging
import os
import json
import hashlib
from io import BytesIO
from datetime import datetime

FTP_HOST    = os.environ.get("VDM_FTP_HOST")
FTP_USER    = os.environ.get("VDM_FTP_USER")
FTP_PASS    = os.environ.get("VDM_FTP_PASS")
FTP_BESTAND = "/Voorraad/voorraadv4.xml"

SHOPIFY_DOMAIN = os.environ.get("SHOPIFY_DOMAIN")
CLIENT_ID      = os.environ.get("SHOPIFY_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("SHOPIFY_CLIENT_SECRET")

# Cache bestand — bewaard tussen runs via GitHub Actions artifact of lokaal
CACHE_BESTAND = "/tmp/vdm_voorraad_cache.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)


def haal_access_token():
    r = requests.post(
        f"https://{SHOPIFY_DOMAIN}/admin/oauth/access_token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    if r.status_code == 200:
        return r.json().get("access_token")
    raise Exception(f"Token ophalen mislukt: {r.status_code} {r.text}")


def download_voorraad():
    log.info("FTP: voorraadv4.xml downloaden...")
    buf = BytesIO()
    with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.retrbinary(f"RETR {FTP_BESTAND}", buf.write)
    data = buf.getvalue()
    xml_hash = hashlib.md5(data).hexdigest()
    log.info(f"XML hash: {xml_hash}")
    return BytesIO(data), xml_hash


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


def laad_cache():
    """Laad vorige voorraadstand uit cache."""
    if os.path.exists(CACHE_BESTAND):
        with open(CACHE_BESTAND) as f:
            return json.load(f)
    return {"hash": None, "voorraad": {}}


def sla_cache_op(xml_hash, voorraad):
    with open(CACHE_BESTAND, 'w') as f:
        json.dump({"hash": xml_hash, "voorraad": voorraad}, f)


def bereken_delta(nieuw, oud):
    """Geef alleen SKUs terug waarvan de voorraad veranderd is."""
    gewijzigd = {}
    for sku, qty in nieuw.items():
        if oud.get(sku) != qty:
            gewijzigd[sku] = qty
    log.info(f"Delta: {len(gewijzigd)} gewijzigd van {len(nieuw)} totaal")
    return gewijzigd


def haal_sku_map(base, headers):
    """Haal SKU → inventory_item_id mapping op uit Shopify."""
    sku_map = {}
    url = f"{base}/variants.json?limit=250&fields=sku,inventory_item_id"
    while url:
        r = requests.get(url, headers=headers, timeout=15)
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
    log.info(f"{len(sku_map)} inventory items geladen")
    return sku_map


def main():
    start = datetime.now()
    log.info("=" * 50)
    log.info(f"Voorraad sync gestart: {start.strftime('%Y-%m-%d %H:%M')}")

    # 1. Download XML + bereken hash
    buf, xml_hash = download_voorraad()
    cache = laad_cache()

    # 2. Als XML niet veranderd is → helemaal stoppen
    if xml_hash == cache["hash"]:
        log.info("✓ XML ongewijzigd — geen updates nodig, klaar.")
        return

    # 3. Parse nieuwe voorraad
    nieuwe_voorraad = parse_voorraad(buf)

    # 4. Bereken delta t.o.v. cache
    delta = bereken_delta(nieuwe_voorraad, cache.get("voorraad", {}))

    if not delta:
        log.info("✓ Geen voorraadwijzigingen gevonden.")
        sla_cache_op(xml_hash, nieuwe_voorraad)
        return

    # 5. Shopify connectie opzetten
    token = haal_access_token()
    HEADERS = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    BASE = f"https://{SHOPIFY_DOMAIN}/admin/api/2024-01"

    locaties = requests.get(f"{BASE}/locations.json", headers=HEADERS, timeout=10).json().get('locations', [])
    locatie_id = locaties[0]['id']

    # 6. Alleen SKU-map ophalen voor gewijzigde SKUs
    # Optim: haal alleen op wat we nodig hebben
    sku_map = haal_sku_map(BASE, HEADERS)

    # 7. Alleen delta updaten
    succesvol = overgeslagen = fouten = 0
    for sku, qty in delta.items():
        inv_item_id = sku_map.get(sku)
        if not inv_item_id:
            overgeslagen += 1
            continue
        r = requests.post(
            f"{BASE}/inventory_levels/set.json",
            headers=HEADERS,
            json={"location_id": locatie_id, "inventory_item_id": inv_item_id, "available": qty},
            timeout=10
        )
        if r.status_code == 200:
            succesvol += 1
            log.info(f"  ✓ {sku}: {cache['voorraad'].get(sku, '?')} → {qty}")
        elif r.status_code == 429:
            log.warning("Rate limit, wacht 10s...")
            time.sleep(10)
            fouten += 1
        else:
            log.warning(f"  ✗ {sku}: {r.status_code}")
            fouten += 1
        time.sleep(0.3)

    # 8. Cache bijwerken met nieuwe stand
    sla_cache_op(xml_hash, nieuwe_voorraad)

    duur = (datetime.now() - start).seconds
    log.info(f"Klaar in {duur}s — ✓ {succesvol} bijgewerkt, ⊘ {overgeslagen} overgeslagen, ✗ {fouten} fouten")


if __name__ == "__main__":
    main()
