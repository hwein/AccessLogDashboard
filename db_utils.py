"""Hilfsfunktionen und Klassen für Datenbankzugriffe."""

import os
import sqlite3
from typing import Iterable, Tuple

import pandas as pd

from utils import load_env

load_env()

DB_FILE = os.environ.get("DB_FILE", "accesslog.db")


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

    INDEX_SQLS = [
        """CREATE UNIQUE INDEX IF NOT EXISTS access_log_id_uindex
        ON access_log (id)""",
        """CREATE INDEX IF NOT EXISTS access_log_is_admin_tech_index
        ON access_log (is_admin_tech)""",
        """CREATE INDEX IF NOT EXISTS access_log_is_bot_index
        ON access_log (is_bot)""",
        """CREATE INDEX IF NOT EXISTS access_log_is_content_index
        ON access_log (is_content)""",
        """CREATE INDEX IF NOT EXISTS access_log_timestamp_index
        ON access_log (timestamp)""",
    ]

    INSERT_SQL = """
    INSERT OR IGNORE INTO access_log (
        timestamp, ip, method, path, query, status, size, referrer, user_agent,
        is_bot, is_admin_tech, is_content, utm_source, utm_medium, utm_campaign
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # ---------------------------------------------------------
    # Statische Helferfunktionen
    # ---------------------------------------------------------
    @staticmethod
    def get_dataframe(
        query: str, params=None, db_file: str = DB_FILE
    ) -> pd.DataFrame:
        """Lädt eine Abfrage als DataFrame aus der Datenbank."""
        with sqlite3.connect(db_file) as con:
            df = pd.read_sql_query(query, con, params=params)
        return df

    @staticmethod
    def load_access_logs(db_file: str = DB_FILE) -> pd.DataFrame:
        """Lädt sämtliche Zeilen der Tabelle ``access_log`` als DataFrame."""
        return AccessLogDB.get_dataframe(
            "SELECT * FROM access_log", db_file=db_file
        )

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
        if force_reload:
            for stmt in self.INDEX_SQLS:
                self._cur.execute(stmt)
        self._con.commit()

    def insert_logs(self, records: Iterable[Tuple]) -> int:
        """Fügt mehrere Logeinträge ein und gibt die Anzahl neuer Zeilen zurück."""
        records = list(records)
        if not records:
            return 0
        before = self._cur.execute(
            "SELECT COUNT(*) FROM access_log"
        ).fetchone()[0]
        self._cur.executemany(self.INSERT_SQL, records)
        self._con.commit()
        after = self._cur.execute(
            "SELECT COUNT(*) FROM access_log"
        ).fetchone()[0]
        return after - before
