import sqlite3
import pandas as pd

DB_FILE = 'accesslog.db'

def get_df(query, params=None, db_file=DB_FILE):
    """Lädt eine Abfrage als DataFrame aus der Datenbank."""
    with sqlite3.connect(db_file) as con:
        df = pd.read_sql_query(query, con, params=params)
    return df

def execute(query, params=None, db_file=DB_FILE):
    """Führt eine Änderungsabfrage (INSERT/UPDATE/DELETE) aus."""
    with sqlite3.connect(db_file) as con:
        cur = con.cursor()
        cur.execute(query, params or ())
        con.commit()
