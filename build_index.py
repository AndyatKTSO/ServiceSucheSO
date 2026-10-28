#!/usr/bin/env python3
"""Service-Verzeichnis und offiziell verlinkte Zuständigkeiten für GitHub Pages.
Keine Vermutung aus allgemeinen 'Weiterführende Links': nur der Abschnitt
'Zuständigkeit' und dort verlinkte Amtsseiten unter /verwaltung/.
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, Tag

BASE = 'https://so.ch/services/'
OUT = Path('site/services.json')
HEADERS = {'User-Agent': 'ServiceSucheGithubPrototype/2.0 (public service directory)', 'Accept': 'text/html'}
# Pfadsegmente der öffentlichen kantonalen Verwaltungsseiten.
DEPARTMENTS = {
    'bau-und-justizdepartement': 'Bau- und Justizdepartement (BJD)',
    'departement-des-innern': 'Departement des Innern (DDI)',
    'departement-fuer-bildung-und-kultur': 'Departement für Bildung und Kultur (DBK)',
    'departement-fuer-bildung-kultur-und-sport': 'Departement für Bildung, Kultur und Sport (DBKS)',
    'bildungs-und-kulturdepartement': 'Departement für Bildung und Kultur (DBK)',
    'finanzdepartement': 'Finanzdepartement (FD)',
    'volkswirtschaftsdepartement': 'Volkswirtschaftsdepartement (VWD)',
    'staatskanzlei': 'Staatskanzlei (STK)',
}


def fetch_url(url):
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            if not response.text.strip():
                raise ValueError('Leere HTML-Antwort')
            return response.text
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def parse_listing(html):
    soup = BeautifulSoup(html, 'html.parser')
    entries = {}
    for a in soup.find_all('a', href=True):
        u = urljoin(BASE, a['href'])
        parts = urlsplit(u)
        if parts.hostname not in ('so.ch', 'www.so.ch'):
            continue
        if not re.fullmatch(r'/services/[^/?#]+/?', parts.path):
            continue
        title_node = a.find(re.compile('^h[1-6]$'))
        title = re.sub(r'\s+', ' ', (title_node or a).get_text(' ', strip=True)).strip()
        if not title or len(title) > 300:
            continue
        clean = urlunsplit(('https', 'so.ch', parts.path.rstrip('/') + '/', '', ''))
        entries[clean] = {'title': title, 'url': clean}
    return entries


def department_from_url(url):
    parsed = urlsplit(url)
    if parsed.hostname not in ('so.ch', 'www.so.ch'):
        return None
    parts = [part.lower() for part in parsed.path.split('/') if part]
    if 'verwaltung' not in parts:
        return None
    idx = parts.index('verwaltung')
    if idx + 1 < len(parts):
        return DEPARTMENTS.get(parts[idx + 1])
    return None


def parse_responsibility(html, base_url):
    """Erfasst Amtsbezeichnungen aus 'Zuständigkeit' und Departemente aus Amtslinks.

    Die weiterführenden Links anderer Abschnitte werden bewusst ignoriert.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for h in soup.find_all(re.compile(r'^h[1-6]$')):
        if h.get_text(' ', strip=True).casefold() != 'zuständigkeit':
            continue
        heading_level = int(h.name[1])
        offices, departments = [], set()
        # Nur den eigenen Inhaltsabschnitt scannen, nicht das Website-Footer.
        for el in h.next_elements:
            if not isinstance(el, Tag):
                continue
            if re.fullmatch(r'h[1-6]', el.name or ''):
                level = int(el.name[1])
                label = re.sub(r'\s+', ' ', el.get_text(' ', strip=True)).strip()
                if level <= heading_level or label.casefold() in ('bleiben sie informiert', 'direktlinks'):
                    break
                # Zwischenüberschriften unter Zuständigkeit entsprechen der
                # ausgeschriebenen Organisationseinheit (z.B. Amt für Umwelt (AFU)).
                if label and label not in offices:
                    offices.append(label)
            elif el.name == 'a' and el.get('href'):
                dep = department_from_url(urljoin(base_url, el['href']))
                if dep:
                    departments.add(dep)
        return offices, sorted(departments)
    return [], []


def enrich(item):
    try:
        html = fetch_url(item['url'])
        responsibility, departments = parse_responsibility(html, item['url'])
        return {**item, 'responsibility': responsibility, 'offices': responsibility, 'departments': departments}, None
    except Exception as exc:
        return {**item, 'responsibility': [], 'offices': [], 'departments': []}, str(exc)


def main():
    items = {}
    signatures = set()
    for page in range(1, 31):
        url = BASE if page == 1 else BASE + '?tx_offers_search%5Bpage%5D=' + str(page)
        batch = parse_listing(fetch_url(url))
        if not batch:
            if page == 1:
                raise RuntimeError('Keine Service-Links erkannt')
            break
        signature = tuple(sorted(batch))
        if signature in signatures:
            break
        signatures.add(signature)
        before = len(items)
        items.update(batch)
        print(f'Seite {page}: {len(batch)} Services, total {len(items)}', flush=True)
        if len(items) == before:
            break
        time.sleep(0.3)
    if len(items) < 300:
        raise RuntimeError(f'Nur {len(items)} Services gefunden – Veröffentlichung abgebrochen')

    enriched = []
    errors = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(enrich, item) for item in items.values()]
        for future in as_completed(futures):
            entry, error = future.result()
            enriched.append(entry)
            if error:
                errors.append((entry['url'], error))
    if len(errors) > max(10, len(items) // 10):
        raise RuntimeError(f'{len(errors)} Detailseiten konnten nicht gelesen werden. Veröffentlichung abgebrochen.')
    identified = sum(bool(item['departments']) for item in enriched)
    print(f'Departements aus Zuständigkeitslinks erkannt: {identified}/{len(enriched)}')
    for url, error in errors[:10]:
        print('WARNUNG:', url, error)
    data = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'source': BASE,
        'count': len(enriched),
        'classified': identified,
        'items': sorted(enriched, key=lambda x: x['title'].casefold()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Geschrieben:', OUT)


if __name__ == '__main__':
    main()
