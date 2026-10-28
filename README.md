# Service-Suche Kanton Solothurn (GitHub-only)

Unabhängiger Prototyp. Die GitHub Action liest die **öffentlichen HTML-Servicelisten** von `https://so.ch/services/`, baut `services.json` und veröffentlicht die Oberfläche via **GitHub Pages**. Der Index wird laut Zeitplan alle 6 Stunden erneuert; GitHub kann geplante Jobs verzögern.

## Einrichtung

1. Neues **öffentliches** Repository auf GitHub erstellen, z. B. `ServiceSucheSO`, Standardbranch `main`.
2. **Den Inhalt** dieses ZIPs in das Repository hochladen (die Verzeichnisse `.github/workflows/`, `scripts/`, `site/` beibehalten). Am einfachsten über **Add file → Upload files**. Falls versteckte `.github`-Ordner nicht mitkommen, via Git lokal hochladen oder die Workflowdatei über **Add file → Create new file** mit dem Namen `.github/workflows/pages.yml` anlegen.
3. Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions** auswählen.
4. **Actions → Service-Suche aktualisieren und veröffentlichen → Run workflow** starten (oder den initialen Push abwarten).
5. Nach erfolgreichem Workflow erscheint die URL unter **Settings → Pages**, üblicherweise `https://BENUTZERNAME.github.io/ServiceSucheSO/`.

## Kontrolle

- Im Actions-Protokoll steht je Seite die Anzahl gelesener Services und zum Schluss die Gesamtzahl (erwartet derzeit ca. 395).
- Die Suche nach `gefahr` sollte mindestens «Gefahrgutbeauftragte (GGB) melden» finden, sofern die Links und Titel korrekt erkannt wurden.
- Falls weniger als 300 Einträge erkannt werden, **bricht der Build ab**, statt einen unvollständigen Index zu veröffentlichen.
- Falls sich die HTML-Struktur der kantonalen Webseite ändert oder automatisierte Abrufe blockiert werden, muss `scripts/build_index.py` angepasst werden.
- GitHub Actions kann geplante Ausführungen verzögern oder bei längerer Inaktivität deaktivieren. Manuelle Ausführung ist jederzeit möglich.

## Datenumfang und Grenzen

- Nur öffentlich sichtbare Titel/Linktexte und Ziel-URLs in der Übersicht; **keine Volltextsuche in Detailseiten**.
- Titel können den Amtsnamen enthalten, wenn er innerhalb derselben Kachel verlinkt ist.
- `gefahrstoff` wird nicht automatisch als Synonym zu `gefahrgut` erkannt. `gefahr` findet beide Wortstämme.
- Kein echter Live-Abruf beim Tippen; Datenstand entspricht der letzten erfolgreichen GitHub Action.
- Der Code ist als Prototyp erstellt. Ein erfolgreicher Abruf aus GitHub Actions konnte hier noch nicht live getestet werden.
