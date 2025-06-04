IGNORED_PATHS = ['/wp-includes/', '/wp-content/', '/wp-json/', '/xmlrpc.php', '/wp-admin', '/wp-login.php', '/wp-cron.php']
IGNORED_REFERRERS = ['leichtgesagt.blog', 'leicht-gesagt.blog', 'www.leichtgesagt.blog', 'www.leicht-gesagt.blog']

def filter_content_paths(df):
    """Filtert technische Pfade aus dem DataFrame."""
    prefixes = tuple(IGNORED_PATHS)
    return df[~df['path'].str.startswith(prefixes)]

def filter_referrers(df):
    """Entfernt interne Referrer aus dem DataFrame."""
    import re
    pattern = "|".join(re.escape(r) for r in IGNORED_REFERRERS)
    return df[~df['referrer'].str.contains(pattern, na=False)]

def apply_date_filter(df, from_date, to_date):
    import pandas as pd
    if 'timestamp' not in df.columns or df.empty:
        return df
    dfi = df.copy()
    dfi['timestamp'] = pd.to_datetime(dfi['timestamp'])
    if from_date:
        dfi = dfi[dfi['timestamp'] >= pd.to_datetime(from_date)]
    if to_date:
        dfi = dfi[dfi['timestamp'] < (pd.to_datetime(to_date) + pd.Timedelta(days=1))]
    return dfi
