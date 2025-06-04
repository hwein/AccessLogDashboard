import tempfile
from pathlib import Path

import logfile_etl as le


def test_extract_utm():
    url = "http://example.com/?utm_source=google&utm_medium=cpc&utm_campaign=test"
    assert le.extract_utm(url) == ("google", "cpc", "test")


def test_extract_utm_none():
    assert le.extract_utm(None) == (None, None, None)
    assert le.extract_utm("-") == (None, None, None)


def test_is_admin_tech():
    assert le.is_admin_tech("/wp-admin/edit.php")
    assert not le.is_admin_tech("/blog/post")


def test_process_logfile(monkeypatch, tmp_path):
    log_path = tmp_path / "access.log"
    log_lines = [
        "127.0.0.1 - - [01/Jan/2021:10:00:00 +0000] \"GET /blog/page.html?utm_source=google&utm_medium=ad&utm_campaign=test HTTP/1.1\" 200 1000 example.com \"http://example.com/\" \"Mozilla/5.0\" \"-\"",
        "127.0.0.2 - - [01/Jan/2021:11:00:00 +0000] \"GET /wp-admin/admin.php HTTP/1.1\" 404 0 example.com \"-\" \"BotAgent\" \"-\"",
    ]
    log_path.write_text("\n".join(log_lines))
    monkeypatch.setattr(le, "is_bot", lambda ua: ua == "BotAgent")
    records = le.process_logfile(str(log_path))
    assert len(records) == 2
    rec1, rec2 = records
    assert rec1[0] == "2021-01-01T10:00:00"
    assert rec1[3] == "/blog/page.html"
    assert rec1[8] == "Mozilla/5.0"
    assert rec1[9] is False
    assert rec1[10] is False
    assert rec1[11] is True
    assert rec1[12:15] == ["google", "ad", "test"]
    assert rec2[9] is True
    assert rec2[10] is True
    assert rec2[11] is False

