import pandas as pd
from flask import Flask, request, redirect, url_for
from collections import Counter
from db_utils import AccessLogDB
from geo_utils import GeoIPLookup
from visualization import to_plotly_figure
from filters import filter_content_paths, filter_referrers, apply_date_filter
from utils import get_date_params, render_dashboard

app = Flask(__name__)
geoip = GeoIPLookup('./geo/GeoLite2-City.mmdb')

#--- Hilfsfunktion (zentral, überall identisch) ---
def get_df_filtered():
    from_date, to_date = get_date_params()
    df_all = AccessLogDB.load_access_logs()
    df_all = apply_date_filter(df_all, from_date, to_date)
    # Flags sauber casten
    if 'is_bot' in df_all:
        df_all['is_bot'] = df_all['is_bot'].astype(int)
    if 'is_content' in df_all:
        df_all['is_content'] = df_all['is_content'].astype(int)
    if 'is_admin_tech' in df_all:
        df_all['is_admin_tech'] = df_all['is_admin_tech'].fillna(0)
        df_all['is_admin_tech'] = df_all['is_admin_tech'].astype(int)
    params = dict(request.args)
    filter_from = from_date
    filter_to = to_date
    return df_all, params, filter_from, filter_to


#--- Default-Route: Redirect auf /overview ---
@app.route("/")
def root():
    return redirect(url_for("overview"))

#--- Übersicht ---
@app.route("/overview")
def overview():
    df_all, params, filter_from, filter_to = get_df_filtered()
    real_users = df_all[(df_all['is_bot'] == 0) & (df_all['is_admin_tech'] == 0)]
    content = real_users[(real_users['method'] == 'GET') & (real_users['is_content'] == 1)].copy()
    content = filter_content_paths(content)
    unique_users = content['ip'].nunique() if not content.empty else 0

    overview = {
        "total": len(df_all),
        "real_users": len(content),
        "unique_users": unique_users,
        "bots": len(df_all[(df_all['is_bot'] == 1)]),
        "errors": int(df_all['status'].astype(str).str.startswith(('4', '5')).sum())
    }

    geo_counts = Counter()
    for ip in content['ip']:
        country, city = geoip.country_city(ip)
        geo_counts[(country, city)] += 1

    top_content_geo = [
        {"country": k[0], "city": k[1], "hits": v}
        for k, v in geo_counts.most_common(10)
    ]

    if not content.empty:
        content['hour'] = pd.to_datetime(content['timestamp']).dt.hour
        htable = content.groupby('hour').size().reset_index(name='count')
        peak_idx = htable['count'].idxmax()
        overview['peak_hour'] = int(htable.iloc[peak_idx]['hour'])
        overview['peak_count'] = int(htable.iloc[peak_idx]['count'])
        hourly_chart = to_plotly_figure(htable['hour'], htable['count'],
                                        "Stunde", "Zugriffe", "Traffic pro Stunde")
    else:
        overview['peak_hour'] = "-"
        overview['peak_count'] = 0
        hourly_chart = "<i>Keine Daten.</i>"

    top_pages = (
        content.groupby('path')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(10)
        .to_dict('records')
    )
    ref = content[content['referrer'] != '-']
    ref = filter_referrers(ref)
    top_referrers = (
        ref.groupby('referrer')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(10)
        .to_dict('records')
    )
    bots = df_all[(df_all['is_bot'] == 1)]
    top_bots = (
        bots.groupby('user_agent')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(10)
        .to_dict('records')
    )

    return render_dashboard(
        "overview.html", "overview", params, filter_from, filter_to,
        overview=overview,
        hourly_chart=hourly_chart,
        top_pages=top_pages,
        top_referrers=top_referrers,
        top_bots=top_bots,
        top_content_geo=top_content_geo,
    )

#--- Errors ---
@app.route("/errors")
def errors():
    df_all, params, filter_from, filter_to = get_df_filtered()
    errors = df_all[df_all['status'].astype(str).str.startswith(('4', '5'))]
    err_detail = (
        errors.groupby(['status', 'path'])
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(20)
        .to_dict('records')
    )
    err_chart_df = errors.groupby('status').size().reset_index(name='count')
    err_chart = to_plotly_figure(err_chart_df['status'], err_chart_df['count'],
                                 "Fehlercode", "Häufigkeit", "Fehlercodes","pie")
    top_error_ips_df = errors.groupby('ip').size().reset_index(name='hits')
    top_error_ips_df = top_error_ips_df.sort_values('hits', ascending=False).head(10)
    top_error_ips = [
        {"ip": row['ip'], "country": geoip.country_city(row['ip'])[0], "hits": row['hits']}
        for _, row in top_error_ips_df.iterrows()
    ]

    return render_dashboard(
        "errors.html", "errors", params, filter_from, filter_to,
        err_detail=err_detail,
        err_chart=err_chart,
        top_error_ips=top_error_ips,
    )

#--- Bots ---
@app.route("/bots")
def bots():
    df_all, params, filter_from, filter_to = get_df_filtered()
    bots = df_all[df_all['is_bot'] == 1].copy()
    bot_counts = (
        bots.groupby('user_agent')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(15)
        .to_dict('records')
    )
    bot_pages = (
        bots.groupby('path')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(15)
        .to_dict('records')
    )
    if not bots.empty:
        bots['date'] = pd.to_datetime(bots['timestamp']).dt.date
        date_counts = bots.groupby('date').size().reset_index(name='count')
        bots_chart = to_plotly_figure(date_counts['date'], date_counts['count'],
                                      "Datum", "Bot-Zugriffe", "Bot-Traffic im Verlauf")
    else:
        bots_chart = "<i>Keine Bot-Daten.</i>"
    return render_dashboard(
        "bots.html", "bots", params, filter_from, filter_to,
        bots_chart=bots_chart,
        bot_counts=bot_counts,
        bot_pages=bot_pages,
    )

#--- Insights ---
@app.route("/insights")
def insights():
    df_all, params, filter_from, filter_to = get_df_filtered()
    real_users = df_all[(df_all['is_bot'] == 0)]
    content = real_users[(real_users['method'] == 'GET') & (real_users['is_content'] == 1)].copy()
    content = filter_content_paths(content)

    top_articles = (
        content.groupby('path')
        .size()
        .reset_index(name='hits')
        .sort_values('hits', ascending=False)
        .head(5)
        .to_dict('records')
    )

    if not content.empty:
        content['weekday'] = pd.to_datetime(content['timestamp']).dt.dayofweek
        weekday_map = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        wtable = content.groupby('weekday').size().reindex(range(7), fill_value=0)
        best_weekday_idx = wtable.idxmax()
        best_weekday = weekday_map[best_weekday_idx]
        weekday_chart = to_plotly_figure([weekday_map[d] for d in range(7)], wtable.values,
                                         "Wochentag", "Zugriffe", "Traffic nach Wochentag")
    else:
        best_weekday = "-"
        weekday_chart = "<i>Keine Daten.</i>"

    if not content.empty:
        content['hour'] = pd.to_datetime(content['timestamp']).dt.hour
        htable = content.groupby('hour').size().reset_index(name='count')
        peak_hour_idx = htable['count'].idxmax()
        best_hour = int(htable.iloc[peak_hour_idx]['hour'])
    else:
        best_hour = "-"

    recommendations = []
    if best_hour != "-":
        recommendations.append(f"Beste Veröffentlichungszeit: <b>{best_hour}:00 Uhr</b> (meiste Zugriffe)")
    if best_weekday != "-":
        recommendations.append(f"Bester Wochentag: <b>{best_weekday}</b> (höchster Traffic)")
    if top_articles:
        art_html = "<b>Top 5 Artikel:</b><ol>"
        for row in top_articles:
            art_html += f"<li>{row['path']} <span class='text-secondary'>({row['hits']} Aufrufe)</span></li>"
        art_html += "</ol>"
        recommendations.append(art_html)

    return render_dashboard(
        "insights.html", "insights", params, filter_from, filter_to,
        recommendations=recommendations,
        weekday_chart=weekday_chart,
    )

#--- UTM ---
@app.route("/utm")
def utm():
    df_all, params, filter_from, filter_to = get_df_filtered()
    real_users = df_all[df_all['is_bot'] == 0]
    content = real_users[(real_users['method'] == 'GET') & (real_users['is_content'] == 1)].copy()
    content = filter_content_paths(content)
    utm = content[
        content['utm_source'].notnull() |
        content['utm_medium'].notnull() |
        content['utm_campaign'].notnull()
    ].copy()
    utm = utm[~((utm['utm_source'].isnull()) & (utm['utm_medium'].isnull()) & (utm['utm_campaign'].isnull()))]
    utm['combo'] = (
        utm['utm_source'].fillna('–') + " | " +
        utm['utm_medium'].fillna('–') + " | " +
        utm['utm_campaign'].fillna('–')
    )
    top_combos = (
        utm.groupby('combo').size().reset_index(name='hits')
        .sort_values('hits', ascending=False).head(15).to_dict('records')
    )
    if not utm.empty:
        utm['date'] = pd.to_datetime(utm['timestamp']).dt.date
        date_chart_df = utm.groupby(['date']).size().reset_index(name='hits')
        utm_chart = to_plotly_figure(date_chart_df['date'], date_chart_df['hits'],
                                     "Tag", "UTM-Zugriffe", "UTM-Traffic im Zeitverlauf")
    else:
        utm_chart = "<i>Keine Daten.</i>"
    top_sources = (
        utm.groupby('utm_source').size().reset_index(name='hits')
        .sort_values('hits', ascending=False).head(10).to_dict('records')
    )
    top_mediums = (
        utm.groupby('utm_medium').size().reset_index(name='hits')
        .sort_values('hits', ascending=False).head(10).to_dict('records')
    )
    top_campaigns = (
        utm.groupby('utm_campaign').size().reset_index(name='hits')
        .sort_values('hits', ascending=False).head(10).to_dict('records')
    )
    return render_dashboard(
        "utm.html", "utm", params, filter_from, filter_to,
        top_combos=top_combos,
        utm_chart=utm_chart,
        top_sources=top_sources,
        top_mediums=top_mediums,
        top_campaigns=top_campaigns,
    )

if __name__ == "__main__":
    app.run(debug=False)
