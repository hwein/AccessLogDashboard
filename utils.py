import os
from datetime import datetime, timedelta, date
from flask import request, render_template, url_for


def load_env(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into ``os.environ``."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)


def render_dashboard(template, tab, params, filter_from, filter_to, **kwargs):
    """
    Baut für alle Tabs und Datum-Shortcuts die passenden URLs,
    reicht alles an das Template weiter (Tabs jetzt als eigene Routen!).
    """
    # Sicherstellen, dass params ein Dict ist und keine None
    params = params or {}

    # Tab-URLs (explizit als View-Funktionsnamen!)
    overview_url = url_for("overview", **params)
    errors_url = url_for("errors", **params)
    bots_url = url_for("bots", **params)
    insights_url = url_for("insights", **params)
    utm_url = url_for("utm", **params)

    # Shortcut-URLs sicher bauen, ohne doppeltes 'preset'
    yesterday_url = url_for_tab_with_preset(tab, params, "yesterday")
    thisweek_url = url_for_tab_with_preset(tab, params, "thisweek")
    lastweek_url = url_for_tab_with_preset(tab, params, "lastweek")
    thismonth_url = url_for_tab_with_preset(tab, params, "thismonth")
    lastmonth_url = url_for_tab_with_preset(tab, params, "lastmonth")
    last30days_url = url_for_tab_with_preset(tab, params, "last30days")

    return render_template(
        template,
        tab=tab,
        params=params,
        overview_url=overview_url,
        errors_url=errors_url,
        bots_url=bots_url,
        insights_url=insights_url,
        utm_url=utm_url,
        yesterday_url=yesterday_url,
        thisweek_url=thisweek_url,
        lastweek_url=lastweek_url,
        thismonth_url=thismonth_url,
        lastmonth_url=lastmonth_url,
        last30days_url=last30days_url,
        filter_from=filter_from,
        filter_to=filter_to,
        **kwargs
    )


def url_for_tab_with_preset(tab, params, preset_name):
    params = params.copy()  # keine Seiteneffekte!
    params.pop("preset", None)
    return url_for(tab, **params, preset=preset_name)


def parse_date_shortcut(preset):
    today = date.today()
    if preset == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1)
    elif preset == "thisweek":
        start = today - timedelta(days=today.weekday())
        return start, today
    elif preset == "lastweek":
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end
    elif preset == "thismonth":
        start = today.replace(day=1)
        return start, today
    elif preset == "lastmonth":
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
        return start, end
    elif preset == "last30days":
        start = today - timedelta(days=29)
        return start, today
    return None, None


def get_date_params():
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    preset = request.args.get("preset")
    if preset:
        f, t = parse_date_shortcut(preset)
        from_date, to_date = str(f), str(t)
    return from_date, to_date
