import sys
import types
import contextlib
from urllib.parse import urlparse, parse_qsl, urlencode

# Minimal Flask stub for tests
class Response:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


def redirect(location):
    return Response(302, {"Location": location})


class RequestHolder:
    def __init__(self):
        self.args = {}

request = RequestHolder()


def url_for(endpoint, **values):
    qs = f"?{urlencode(values)}" if values else ""
    return f"/{endpoint}{qs}"


flask_stub = types.ModuleType("flask")


class Flask:
    def __init__(self, name):
        self.view_funcs = {}

    def route(self, path):
        def decorator(func):
            self.view_funcs[path] = func
            self.view_funcs[func.__name__] = func
            return func
        return decorator

    def test_client(self):
        app = self

        class Client:
            def get(self, path):
                func = app.view_funcs[path]
                return func()

        return Client()

    @contextlib.contextmanager
    def test_request_context(self, path):
        global request, flask_stub
        parsed = urlparse(path)
        args = dict(parse_qsl(parsed.query))
        old_args = request.args
        request.args = args
        flask_stub.request = request
        try:
            yield
        finally:
            request.args = old_args
            flask_stub.request = request


flask_stub.Flask = Flask
flask_stub.request = request
flask_stub.redirect = redirect
flask_stub.url_for = url_for
flask_stub.render_template = lambda *a, **k: (a, k)
sys.modules.setdefault("flask", flask_stub)

# Minimal paramiko stub
paramiko_stub = types.ModuleType("paramiko")
sys.modules.setdefault("paramiko", paramiko_stub)

# Minimal geoip2 stub
geoip2_stub = types.ModuleType("geoip2")
geoip2_stub.database = types.SimpleNamespace(Reader=lambda path: types.SimpleNamespace(city=lambda ip: None))
sys.modules.setdefault("geoip2", geoip2_stub)
sys.modules.setdefault("geoip2.database", geoip2_stub.database)

# Minimal plotly stub
plotly_stub = types.ModuleType("plotly")
plotly_stub.graph_objs = types.SimpleNamespace(Figure=lambda *a, **k: None)
sys.modules.setdefault("plotly", plotly_stub)
sys.modules.setdefault("plotly.graph_objs", plotly_stub.graph_objs)
plotly_stub.io = types.SimpleNamespace(to_html=lambda fig, full_html=False: "<html>")
sys.modules.setdefault("plotly.io", plotly_stub.io)
plotly_stub.graph_objs.Bar = lambda *a, **k: None
plotly_stub.graph_objs.Scatter = lambda *a, **k: None
plotly_stub.graph_objs.Pie = lambda *a, **k: None

# Minimal pandas stub
pandas_stub = types.ModuleType('pandas')
pandas_stub.DataFrame = dict
pandas_stub.read_sql_query = lambda q, con, params=None: {'q': q, 'params': params}
sys.modules.setdefault('pandas', pandas_stub)
