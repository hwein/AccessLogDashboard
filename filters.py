IGNORED_PATHS = ['/wp-includes/', '/wp-content/', '/wp-json/', '/xmlrpc.php', '/wp-admin', '/wp-login.php', '/wp-cron.php']
IGNORED_REFERRERS = ['leichtgesagt.blog', 'leicht-gesagt.blog', 'www.leichtgesagt.blog', 'www.leicht-gesagt.blog']

def filter_content_paths(df):
    for tech in IGNORED_PATHS:
        df = df[~df['path'].str.startswith(tech)]
    return df

def filter_referrers(df):
    for d in IGNORED_REFERRERS:
        df = df[~df['referrer'].str.contains(d, na=False)]
    return df

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
