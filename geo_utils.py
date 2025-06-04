import geoip2.database


class GeoIPLookup:
    _instance = None
    """Singleton wrapper for GeoIP city lookups."""

    def __new__(cls, db_path="./GeoLite2-City.mmdb"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reader = geoip2.database.Reader(db_path)
            cls._instance._cache = {}
        return cls._instance

    def country_city(self, ip):
        if ip in self._cache:
            return self._cache[ip]
        try:
            resp = self.reader.city(ip)
            country = resp.country.name or resp.country.iso_code or "?"
            city = resp.city.name or "-"
            result = (country, city)
        except Exception:
            result = ("?", "-")
        self._cache[ip] = result
        return result
