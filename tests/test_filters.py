import sys
import types
import datetime

import filters as f


class FakeSeries(list):
    @property
    def str(self):
        outer = self
        class StrOps:
            def startswith(self, prefixes):
                return FakeSeries([val.startswith(prefixes) for val in outer])
            def contains(self, pattern, na=False):
                import re
                regex = re.compile(pattern)
                return FakeSeries([bool(regex.search(val)) if val is not None else False for val in outer])
        return StrOps()
    def __invert__(self):
        return FakeSeries([not x for x in self])
    def __ge__(self, other):
        return FakeSeries([val >= other for val in self])
    def __lt__(self, other):
        return FakeSeries([val < other for val in self])


class FakeDataFrame:
    def __init__(self, data):
        self.data = {k: (v if isinstance(v, FakeSeries) else FakeSeries(v)) for k, v in data.items()}
    @property
    def columns(self):
        return list(self.data.keys())
    @property
    def empty(self):
        return len(self) == 0
    def copy(self):
        return FakeDataFrame({k: FakeSeries(list(v)) for k, v in self.data.items()})
    def __len__(self):
        return len(next(iter(self.data.values()), []))
    def __getitem__(self, key):
        if isinstance(key, str):
            return self.data[key]
        mask = list(key)
        new = {k: FakeSeries([val for val, keep in zip(v, mask) if keep]) for k, v in self.data.items()}
        return FakeDataFrame(new)
    def __setitem__(self, key, value):
        if not isinstance(value, FakeSeries):
            value = FakeSeries(value)
        self.data[key] = value


def test_filter_content_paths():
    df = FakeDataFrame({'path': FakeSeries(['/wp-login.php', '/blog/post'])})
    result = f.filter_content_paths(df)
    assert result['path'] == ['/blog/post']


def test_filter_referrers():
    df = FakeDataFrame({'referrer': FakeSeries(['https://leichtgesagt.blog', 'https://google.com'])})
    result = f.filter_referrers(df)
    assert result['referrer'] == ['https://google.com']


def test_apply_date_filter(monkeypatch):
    def to_datetime(val):
        if isinstance(val, FakeSeries):
            return FakeSeries([datetime.datetime.fromisoformat(v) for v in val])
        return datetime.datetime.fromisoformat(val)
    pd_stub = types.ModuleType('pandas')
    pd_stub.to_datetime = to_datetime
    pd_stub.Timedelta = datetime.timedelta
    monkeypatch.setitem(sys.modules, 'pandas', pd_stub)

    df = FakeDataFrame({'timestamp': FakeSeries(['2021-01-01', '2021-01-05', '2021-01-10'])})
    result = f.apply_date_filter(df, '2021-01-02', '2021-01-06')
    assert result['timestamp'] == [datetime.datetime(2021, 1, 5)]

    df_no_ts = FakeDataFrame({'other': FakeSeries([1])})
    assert f.apply_date_filter(df_no_ts, '2021-01-01', '2021-01-02') is df_no_ts
