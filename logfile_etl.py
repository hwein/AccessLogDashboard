import os
import re
import gzip
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import argparse
import logging

from bot_utils import is_bot

import paramiko
from db_utils import AccessLogDB
from utils import load_env
from filters import IGNORED_PATH_PREFIXES

load_env()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class SFTPConfig:
    host: str
    port: int
    user: str
    password: str


@dataclass
class ETLConfig:
    sftp: SFTPConfig
    local_dir: str
    mode: str
    force_reload: bool
    db_file: str
    logfile_pattern: str


def get_config() -> ETLConfig:
    """Return configuration loaded from environment variables."""
    sftp = SFTPConfig(
        host=os.environ.get("SFTP_HOST", "xxxxxx"),
        port=int(os.environ.get("SFTP_PORT", 22)),
        user=os.environ.get("SFTP_USER", "xxxxxx"),
        password=os.environ.get("SFTP_PASSWORD", "xxxxxx"),
    )
    return ETLConfig(
        sftp=sftp,
        local_dir=os.environ.get("LOCAL_DIR", "./logs"),
        mode=os.environ.get("MODE", "bulk"),
        force_reload=os.environ.get("FORCE_RELOAD", "False").lower() == "true",
        db_file=os.environ.get("DB_FILE", "accesslog.db"),
        logfile_pattern=os.environ.get(
            "LOGFILE_PATTERN", r"access\.log\.\d+(\.\d+)?(\.gz)?$"
        ),
    )


CONFIG: ETLConfig = get_config()


def parse_args():
    """Parse command line arguments for optional configuration overrides."""
    parser = argparse.ArgumentParser(description="Download and import log files")
    parser.add_argument(
        "--force-reload",
        dest="force_reload",
        action=argparse.BooleanOptionalAction,
        help="Override FORCE_RELOAD from .env",
    )
    parser.add_argument(
        "--mode",
        choices=["bulk", "daily"],
        help="Override MODE from .env",
    )
    return parser.parse_args()


# Vorab kompilierte Pattern für Logzeilen und Bot-Erkennung
LOG_PATTERN = re.compile(
    r"(?P<ip>\S+) \S+ \S+ \[(?P<time>.+?)\] \"(?P<method>\S+) (?P<url>\S+)(?: \S+)?\" (?P<status>\d{3}) (?P<size>\S+) (?P<vhost>\S+) \"(?P<referrer>.*?)\" \"(?P<user_agent>.*?)\" \"(?P<last>.*?)\""
)

# Bot-Erkennung ueber externe Liste


def clear_local_dir(local_dir):
    """Löscht alle Dateien im lokalen Download-Ordner."""
    for f in os.listdir(local_dir):
        file_path = os.path.join(local_dir, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                logger.info(f"Lösche lokale Datei: {file_path}")
        except Exception as e:
            logger.error(f"Fehler beim Löschen von {file_path}: {e}")


# --- SFTP Download Funktion ---
def sftp_download_logs(config: ETLConfig):
    sftp_cfg = config.sftp
    local_dir = config.local_dir
    logfile_pattern = re.compile(config.logfile_pattern)
    os.makedirs(local_dir, exist_ok=True)
    clear_local_dir(local_dir)
    logger.info("Verbinde mit SFTP-Server ...")
    client = paramiko.Transport((sftp_cfg.host, sftp_cfg.port))
    try:
        client.connect(username=sftp_cfg.user, password=sftp_cfg.password)
        sftp = paramiko.SFTPClient.from_transport(client)
        files = sftp.listdir(".")
        logger.info(f"Gefundene Dateien auf SFTP: {files}")

        # Dateifilter: access.log.*, KEINE .gz, KEIN traffic.db, sftp.log, access.log.current
        logfiles = [
            f
            for f in files
            if logfile_pattern.match(f)
            and f not in {"traffic.db", "sftp.log", "access.log.current"}
        ]
        logger.info(f"Logfiles nach Pattern-Match: {logfiles}")
        if config.mode == "daily":
            mtimes = [(f, sftp.stat(f).st_mtime) for f in logfiles]
            if mtimes:
                mtimes.sort(key=lambda x: x[1], reverse=True)
                logfiles = [mtimes[0][0]]
                logger.info(f"Daily Mode: Verarbeite nur Datei: {logfiles[0]}")
            else:
                logger.info("Daily Mode: Keine passenden Logfiles gefunden!")
                logfiles = []
        for fname in logfiles:
            remote = fname
            local = os.path.join(local_dir, fname)
            if not os.path.exists(local):
                logger.info(f"Lade {fname} ...")
                sftp.get(remote, local)
            else:
                logger.info(f"{fname} existiert bereits lokal, wird übersprungen.")
    finally:
        try:
            sftp.close()
        finally:
            client.close()
    # GZ entpacken falls nötig
    for fname in logfiles:
        if fname.endswith(".gz"):
            gz_path = os.path.join(local_dir, fname)
            out_path = os.path.join(local_dir, fname[:-3])
            if not os.path.exists(out_path):
                logger.info(f"Entpacke: {gz_path} -> {out_path}")
                with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            else:
                logger.info(f"{out_path} existiert bereits lokal, wird übersprungen.")
    # Gib alle Log-Dateien (entpackt, falls nötig) zurück
    all_files = [
        f
        for f in os.listdir(local_dir)
        if logfile_pattern.match(f)
        and f != "access.log.current"
        and not f.endswith(".gz")
    ]
    logger.info(f"Dateien für Import: {all_files}")
    return [os.path.join(local_dir, f) for f in all_files]


# --- Duplikat-Erkennung & DB-Initialisierung ---


def is_admin_tech(path):
    """True, wenn der Pfad zu administrativen WordPress-Bereichen gehört."""
    return path.startswith(IGNORED_PATH_PREFIXES)


def extract_utm(referrer):
    utm_source = utm_medium = utm_campaign = None
    if referrer and referrer != "-":
        params = parse_qs(urlparse(referrer).query)
        utm_source = params.get("utm_source", [None])[0]
        utm_medium = params.get("utm_medium", [None])[0]
        utm_campaign = params.get("utm_campaign", [None])[0]
    return utm_source, utm_medium, utm_campaign


def process_logfile(filepath):
    logger.info(f"Starte Verarbeitung von {filepath} ...")
    records = []
    total_lines = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            m = LOG_PATTERN.match(line)
            if not m:
                continue
            d = m.groupdict()
            ts = datetime.strptime(d["time"].split()[0], "%d/%b/%Y:%H:%M:%S")
            d["timestamp"] = ts.isoformat()
            d["path"] = urlparse(d["url"]).path
            d["query"] = urlparse(d["url"]).query
            d["is_bot"] = is_bot(d["user_agent"])
            d["is_admin_tech"] = is_admin_tech(d["path"])
            d["is_content"] = not d["is_admin_tech"]
            utm_source, utm_medium, utm_campaign = extract_utm(d["referrer"])
            d["utm_source"] = utm_source
            d["utm_medium"] = utm_medium
            d["utm_campaign"] = utm_campaign
            # vhost wird nicht gebraucht, deshalb hier ignoriert!
            records.append(
                [
                    d["timestamp"],
                    d["ip"],
                    d["method"],
                    d["path"],
                    d["query"],
                    d["status"],
                    d["size"],
                    d["referrer"],
                    d["user_agent"],
                    d["is_bot"],
                    d["is_admin_tech"],
                    d["is_content"],
                    d["utm_source"],
                    d["utm_medium"],
                    d["utm_campaign"],
                ]
            )
    logger.info(
        f"{len(records)} von {total_lines} Zeilen in {filepath} erfolgreich geparst."
    )
    return records


def main(config: ETLConfig = CONFIG):
    files = sftp_download_logs(config)
    total_imported = 0
    with AccessLogDB(config.db_file) as db:
        db.init_db(config.force_reload)
        for f in files:
            logger.info(f"Verarbeite: {f}")
            data = process_logfile(f)
            imported = db.insert_logs(data)
            skipped = len(data) - imported
            logger.info(f"{imported} neue Zeilen aus {f} importiert.")
            logger.info(
                f"{skipped} Zeilen aus {f} waren Duplikate und wurden übersprungen."
            )
            total_imported += imported
    logger.info(
        f"Import abgeschlossen. Insgesamt {total_imported} Zeilen verarbeitet (nur neue gespeichert)."
    )


if __name__ == "__main__":
    args = parse_args()
    config = replace(CONFIG)
    if args.force_reload is not None:
        config.force_reload = args.force_reload
    if args.mode:
        config.mode = args.mode
    main(config)
