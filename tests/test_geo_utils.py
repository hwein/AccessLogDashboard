import sys
import types
import importlib


def setup_geoip(monkeypatch):
    class FakeReader:
        def __init__(self, path):
            self.path = path
            self.calls = []
        class Response:
            def __init__(self):
                self.country = types.SimpleNamespace(name='X', iso_code='X')
                self.city = types.SimpleNamespace(name='Y')
        def city(self, ip):
            self.calls.append(ip)
            if ip == 'bad':
                raise Exception('boom')
            return self.Response()
    database_stub = types.SimpleNamespace(Reader=lambda path: FakeReader(path))
    geoip2_stub = types.ModuleType('geoip2')
    geoip2_stub.database = database_stub
    monkeypatch.setitem(sys.modules, 'geoip2', geoip2_stub)
    monkeypatch.setitem(sys.modules, 'geoip2.database', database_stub)
    return FakeReader


def test_geoip_lookup(monkeypatch):
    FakeReader = setup_geoip(monkeypatch)
    if 'geo_utils' in sys.modules:
        geo_utils = importlib.reload(sys.modules['geo_utils'])
    else:
        geo_utils = importlib.import_module('geo_utils')
    geo_utils.GeoIPLookup._instance = None

    lookup1 = geo_utils.GeoIPLookup('db_path')
    lookup2 = geo_utils.GeoIPLookup('ignored')
    assert lookup1 is lookup2
    assert lookup1.reader.path == 'db_path'

    assert lookup1.country_city('1.1.1.1') == ('X', 'Y')
    # second call uses cache
    assert lookup1.country_city('1.1.1.1') == ('X', 'Y')
    assert lookup1.reader.calls == ['1.1.1.1']

    assert lookup1.country_city('bad') == ('?', '-')
    assert lookup1.reader.calls == ['1.1.1.1', 'bad']
