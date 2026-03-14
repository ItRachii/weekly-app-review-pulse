import sqlite3
import os
import requests
from google_play_scraper import app as gplay_app

db_path = r'd:\development\weekly-app-review-pulse\data\pulse.db'

def get_app_store_icon(app_id):
    try:
        url = f"https://itunes.apple.com/lookup?id={app_id}"
        resp = requests.get(url).json()
        if resp.get('resultCount', 0) > 0:
            return resp['results'][0].get('artworkUrl512', '')
    except:
        pass
    return ''

def get_play_store_icon(app_id):
    try:
        res = gplay_app(app_id)
        return res.get('icon', '')
    except:
        return ''

with sqlite3.connect(db_path) as conn:
    # ensure column exists just in case
    try:
        conn.execute("ALTER TABLE applications ADD COLUMN logo_url TEXT")
    except:
        pass
    apps = conn.execute("SELECT app_name, playstore_id, appstore_id FROM applications").fetchall()
    for a_name, pid, aid in apps:
        icon_url = get_play_store_icon(pid)
        if not icon_url:
            icon_url = get_app_store_icon(aid)
        if icon_url:
            conn.execute("UPDATE applications SET logo_url = ? WHERE app_name = ?", (icon_url, a_name))
            print(f"Updated {a_name} with logo {icon_url}")
        else:
            print(f"Failed to find logo for {a_name}")
    conn.commit()
