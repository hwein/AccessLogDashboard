"""Hilfsfunktionen und Klassen für Datenbankzugriffe."""

import os
import sqlite3
from typing import Iterable, Tuple

import pandas as pd


def load_env(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)


load_env()

DB_FILE = os.environ.get("DB_FILE", "accesslog.db")


def get_df(query: str, params=None, db_file: str = DB_FILE) -> pd.DataFrame:
    """Lädt eine Abfrage als DataFrame aus der Datenbank."""
    with sqlite3.connect(db_file) as con:
        df = pd.read_sql_query(query, con, params=params)
    return df


def execute(query: str, params=None, db_file: str = DB_FILE) -> None:
    """Führt eine Änderungsabfrage (INSERT/UPDATE/DELETE) aus."""
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(query, params or ())
        con.commit()


class AccessLogDB:
    """Kapselt alle Datenbankoperationen für die Access-Logs."""

    TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ip TEXT,
        method TEXT,
        path TEXT,
        query TEXT,
        status INTEGER,
        size TEXT,
        referrer TEXT,
        user_agent TEXT,
        is_bot BOOLEAN,
        is_admin_tech BOOLEAN,
        is_content BOOLEAN,
        utm_source TEXT,
        utm_medium TEXT,
        utm_campaign TEXT,
        UNIQUE(timestamp, ip, method, path, query, user_agent)
    )
    """

    INSERT_SQL = """
    INSERT OR IGNORE INTO access_log (
        timestamp, ip, method, path, query, status, size, referrer, user_agent,
        is_bot, is_admin_tech, is_content, utm_source, utm_medium, utm_campaign
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._con = None
        self._cur = None

    def __enter__(self) -> "AccessLogDB":
        self._con = sqlite3.connect(self.db_file)
        self._cur = self._con.cursor()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._con:
            self._con.close()

    # ---------------------------------------------------------
    # Initialisierung und Inserts
    # ---------------------------------------------------------
    def init_db(self, force_reload: bool = False) -> None:
        """Erzeugt die Datenbanktabelle und löscht sie optional vorher."""
        if force_reload:
            self._cur.execute("DROP TABLE IF EXISTS access_log")
        self._cur.execute(self.TABLE_SQL)
        self._con.commit()

    def insert_logs(self, records: Iterable[Tuple]) -> int:
        """Fügt mehrere Logeinträge ein und gibt die Anzahl neuer Zeilen zurück."""
        records = list(records)
        if not records:
            return 0
        before = self._cur.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
        self._cur.executemany(self.INSERT_SQL, records)
        self._con.commit()
        after = self._cur.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
        return after - before

