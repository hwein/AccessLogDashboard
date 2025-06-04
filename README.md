# AccessLogDashboard

Eine kleine Python-Anwendung zum Analysieren von Server-Logfiles. 
Logfiles werden per SFTP heruntergeladen, in eine SQLite-Datenbank importiert
und anschließend über ein Flask-Dashboard ausgewertet.

## Funktionen

- Import von Access-Logs mittels `logfile_etl.py`
- Speicherung der Daten in einer SQLite-Datenbank (Datei via `DB_FILE` definierbar)
- Web-Dashboard (`analytics_dashboard.py`) mit Übersichten zu Fehlern,
  Bots, Inhaltsaufrufen und UTM-Parametern
- Datumsfilter und einfache Diagramme mit Plotly
- Geolokalisierung über die MaxMind GeoLite2 City-Datenbank

## Installation

1. Python 3.9 oder neuer installieren.
2. Abhängigkeiten installieren:
   ```bash
   pip install pandas flask paramiko geoip2 plotly
   ```
3. `.env.example` nach `.env` kopieren und die SFTP-Zugangsdaten sowie `DB_FILE` anpassen.
4. Die GeoLite2 City-Datenbank von [MaxMind](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
   herunterladen und unter `geo/GeoLite2-City.mmdb` ablegen.
5. Die Datei `bot_user_agents.txt` enthält Erkennungsmerkmale bekannter Bots und kann bei Bedarf angepasst werden.

## Verwendung

### Logfiles importieren

```
python logfile_etl.py [--force-reload] [--no-force-reload] [--mode bulk|daily]
```

Dies lädt die Logfiles vom im `.env` definierten Server, parst sie und
schreibt neue Einträge in die SQLite-Datenbank. Mit den optionalen
Parametern `--force-reload`/`--no-force-reload` sowie `--mode` können die
entsprechenden Werte aus der `.env` überschrieben werden.

Beispielaufruf, um den Modus auf `bulk` zu setzen und `force_reload`
auf `false` zu stellen:

```bash
python logfile_etl.py --mode bulk --no-force-reload
```

### Dashboard starten

```
python analytics_dashboard.py
```

Das Dashboard ist danach unter <http://localhost:5000/> erreichbar.

## Projektstruktur

- `logfile_etl.py` – Download und Import der Logfiles
- `analytics_dashboard.py` – Startet das Flask-Dashboard
- `templates/` – HTML-Vorlagen für die Darstellung
- `logs/` – Lokales Verzeichnis für heruntergeladene Access-Logs
- `geo/` – Lokales Verzeichnis für MaxMind-Geodaten
- `db_utils.py`, `bots_utils.py`, `filters.py`, `geo_utils.py`, `utils.py` – Hilfsfunktionen

Viel Spaß beim Analysieren!
