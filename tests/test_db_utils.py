import sqlite3

import db_utils as du


def test_get_dataframe(monkeypatch):
    calls = {}
    def fake_read_sql_query(query, con, params=None):
        calls['query'] = query
        calls['params'] = params
        calls['connected'] = isinstance(con, sqlite3.Connection)
        return 'DF'

    monkeypatch.setattr(du.pd, 'read_sql_query', fake_read_sql_query)

    result = du.AccessLogDB.get_dataframe('SELECT 1', params=[1], db_file=':memory:')
    assert result == 'DF'
    assert calls == {'query': 'SELECT 1', 'params': [1], 'connected': True}


def test_load_access_logs(monkeypatch):
    monkeypatch.setattr(du.AccessLogDB, 'get_dataframe', staticmethod(lambda query, db_file='': (query, db_file)))
    assert du.AccessLogDB.load_access_logs('file.db') == ('SELECT * FROM access_log', 'file.db')


def test_insert_logs(tmp_path):
    db_path = tmp_path / 'test.db'
    with du.AccessLogDB(str(db_path)) as db:
        db.init_db(force_reload=True)
        records = [(
            '2021-01-01T00:00:00', '127.0.0.1', 'GET', '/', '', 200, '0', '-', 'UA',
            False, False, True, None, None, None
        )]
        inserted = db.insert_logs(records)
        assert inserted == 1
        inserted_none = db.insert_logs([])
        assert inserted_none == 0
