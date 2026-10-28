#!/usr/bin/env python3
"""Liest die öffentlich zugänglichen Service-Übersichtsseiten von so.ch.
Die HTML-Struktur kann sich ändern; bei unplausiblen Daten wird der Build abgebrochen.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

BASE = 'https://so.ch/services/'
OUT = Path('site/services.json')
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'ServiceSucheGithubPrototype/1.0 (public service directory)', 'Accept': 'text/html'})


def fetch(page):
    url = BASE if page == 1 else BASE + '?tx_offers_search%5Bpage%5D=' + str(page)
    for attempt in range(3):
        try:
            res = SESSION.get(url, timeout=30)
            res.raise_for_status()
            if not res.text.strip():
                raise ValueError('Leere HTML-Antwort')
            return res.text
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    entries = {}
    # Detailseiten unter /services/<slug>/; Such- und Paginierungslinks ausgeschlossen.
    for a in soup.find_all('a', href=True):
        u = urljoin(BASE, a['href'])
        parts = urlsplit(u)
        if parts.hostname not in ('so.ch', 'www.so.ch'):
            continue
        if not re.fullmatch(r'/services/[^/?#]+/?', parts.path):
            continue
        if parts.path.rstrip('/') == '/services':
            continue
        clean = urlunsplit(('https', 'so.ch', parts.path.rstrip('/') + '/', '', ''))
        heading = a.find(re.compile('^h[1-6]$'))
        # Manche Kacheln enthalten Titel und Amtsname im selben Link.
        # Den gesamten sichtbaren Linktext behalten, damit die Suche nichts verliert.
        title = (heading or a).get_text(' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()
        if not title or len(title) > 300:
            continue
        entries[clean] = {'title': title, 'url': clean}
    return entries


def main():
    items = {}
    previous_signatures = set()
    for page in range(1, 31):
        batch = parse(fetch(page))
        if not batch:
            if page == 1:
                raise RuntimeError('Auf der Startseite wurden keine Service-Links erkannt.')
            break
        signature = tuple(sorted(batch))
        if signature in previous_signatures:
            break
        previous_signatures.add(signature)
        before = len(items)
        items.update(batch)
        print(f'Seite {page}: {len(batch)} Links, gesamt {len(items)}')
        if len(items) == before:
            break
        time.sleep(0.4)
    # 2026-10: ca. 395 Einträge. Deutlich weniger deutet auf fehlgeschlagenen Abruf hin.
    if len(items) < 300:
        raise RuntimeError(f'Nur {len(items)} Services gefunden (erwartet mindestens 300). Nichts publiziert.')
    data = {'updated': datetime.now(timezone.utc).isoformat(),
            'source': BASE,
            'count': len(items),
            'items': sorted(items.values(), key=lambda x: x['title'].casefold())}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Geschrieben:', OUT, 'mit', len(items), 'Einträgen')


if __name__ == '__main__':
    main()

