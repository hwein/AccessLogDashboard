import os
import datetime
from flask import Flask

import utils


def test_load_env(tmp_path, monkeypatch):
    env_file = tmp_path / 'test.env'
    env_file.write_text('A=1\n#comment\nB=2\n')
    monkeypatch.delenv('A', raising=False)
    monkeypatch.delenv('B', raising=False)
    utils.load_env(str(env_file))
    assert os.environ['A'] == '1'
    assert os.environ['B'] == '2'


def test_parse_date_shortcut(monkeypatch):
    class DummyDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2021, 1, 15)
    monkeypatch.setattr(utils, 'date', DummyDate)
    start, end = utils.parse_date_shortcut('yesterday')
    assert start == datetime.date(2021, 1, 14)
    assert end == datetime.date(2021, 1, 14)
    start, end = utils.parse_date_shortcut('lastweek')
    assert start == datetime.date(2021, 1, 4)
    assert end == datetime.date(2021, 1, 10)


def test_url_for_tab_with_preset():
    app = Flask(__name__)

    @app.route('/test')
    def test():
        return ''

    with app.test_request_context('/'):
        url = utils.url_for_tab_with_preset('test', {'a': 'b', 'preset': 'x'}, 'y')
        assert url == '/test?a=b&preset=y'


def test_get_date_params(monkeypatch):
    app = Flask(__name__)
    class DummyDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2021, 1, 15)
    monkeypatch.setattr(utils, 'date', DummyDate)
    with app.test_request_context('/?preset=yesterday'):
        assert utils.get_date_params() == ('2021-01-14', '2021-01-14')
    with app.test_request_context('/?from=2021-01-01&to=2021-01-02'):
        assert utils.get_date_params() == ('2021-01-01', '2021-01-02')
