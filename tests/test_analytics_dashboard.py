import types
import sys

import pytest

# Provide a minimal pandas stub before importing the module
pandas_stub = types.ModuleType("pandas")
pandas_stub.DataFrame = dict
sys.modules.setdefault("pandas", pandas_stub)

import analytics_dashboard as ad


def test_root_redirect():
    client = ad.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/overview")


class FakeSeries(list):
    def astype(self, typ):
        return FakeSeries([typ(x) if x is not None else 0 for x in self])

    def fillna(self, val):
        return FakeSeries([val if x is None else x for x in self])


class FakeDataFrame(dict):
    def __contains__(self, item):
        return dict.__contains__(self, item)

    def __getitem__(self, item):
        return dict.__getitem__(self, item)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)


def test_get_df_filtered(monkeypatch):
    df = FakeDataFrame({
        "is_bot": FakeSeries([0, 1]),
        "is_content": FakeSeries([1, 0]),
        "is_admin_tech": FakeSeries([0, None]),
    })

    monkeypatch.setattr(ad.AccessLogDB, "load_access_logs", staticmethod(lambda: df))
    monkeypatch.setattr(ad, "apply_date_filter", lambda d, f, t: d)
    monkeypatch.setattr(ad, "get_date_params", lambda: ("2021-01-01", "2021-01-31"))

    with ad.app.test_request_context("/overview"):
        result_df, params, f_from, f_to = ad.get_df_filtered()

    assert isinstance(result_df, FakeDataFrame)
    assert result_df["is_admin_tech"] == [0, 0]
    assert f_from == "2021-01-01"
    assert f_to == "2021-01-31"
    assert params == {}

