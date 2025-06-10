from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime, timezone, timedelta
import sys
from pytube import Playlist as PyTubePlaylist
import threading
import time
import yt_dlp
import musicbrainzngs
import re

# Flask app setup
app = Flask(__name__)

# YoutubeDL options
ydl_opts = {
    'quiet': True,
    'skip_download': True,
    'no_warnings': True
}

# Musicbrainz agent
musicbrainzngs.set_useragent("SearchArtist", "0.1", "your-email@example.com")

# Directory and DB setup
os.makedirs("db", exist_ok=True)
db_path = os.path.join("db", "database.db")

# Initialize database and config
def initialize_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            PlaylistURL TEXT NOT NULL UNIQUE,
            PlaylistTitle TEXT,
            Songs INTEGER,
            Populated TEXT,
            CreatedOn TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL UNIQUE,
            Value TEXT,
            Description TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            YoutubeId TEXT NOT NULL UNIQUE,
            VideoTitle TEXT,
            MusicBrainzId TEXT,
            MusicBrainzArtist TEXT,        
            CreatedOn TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT 1 FROM config WHERE Name = 'ScheduledRun'")
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO config (ID, Name, Value, Description)
            VALUES (1, 'ScheduledRun', '14400', 'This configuration value contains the scheduled run time in seconds.')
        """)
    cursor.execute("SELECT 1 FROM config WHERE Name = 'LastRun'")
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO config (Name, Value, Description)
            VALUES ('LastRun', '', 'The last time playlists were updated.')
        """)
    conn.commit()
    conn.close()

initialize_database()

# --- Utility Functions ---
def extract_youtube_id(url):
    match = re.search(r'(?:v=|be/)([\w-]{11})', url)
    return match.group(1) if match else None


def search_recordings_by_artist(text):
    # Clean text
    cleaned = re.sub(r"\s*[\[\(\{][^\]\)\}]*[\]\)\}]", "", text).strip()
    try:
        if '-' in cleaned:
            hyphen1, hyphen2 = map(str.strip, cleaned.split('-', 1))
            result = musicbrainzngs.search_recordings(artist=hyphen1, recording=hyphen2, limit=5)
            if result['recording-list']:
                return result['recording-list'][0]['artist-credit'][0]['artist']
            result = musicbrainzngs.search_recordings(artist=hyphen2, recording=hyphen1)
            if result['recording-list']:
                return result['recording-list'][0]['artist-credit'][0]['artist']

            result = musicbrainzngs.search_artists(artist=hyphen1)
            for item in result['artist-list']:
                if item['name'].upper() == hyphen1.upper() and item.get('country') == 'HU':
                    return item
            for item in result['artist-list']:
                if item['name'].upper() == hyphen1.upper() and item.get('country') == 'US':
                    return item
            for item in result['artist-list']:
                if item['name'].upper() == hyphen1.upper() and item.get('country') == 'GB':
                    return item
            for item in result['artist-list']:
                if item['name'].upper() == hyphen1.upper() and item.get('country') == 'IT':
                    return item
            for item in result['artist-list']:
                if item['name'] == hyphen1:
                    return item
            result = musicbrainzngs.search_artists(artist=hyphen2)
            for item in result['artist-list']:
                if item['name'] == hyphen2:
                    return item
                
        result = musicbrainzngs.search_artists(artist=cleaned)
        if not result['artist-list']:
            print("No artist found.")
            return
        for item in result['artist-list']:
            if int(item['ext:score']) > 95:
                return item
        return None
    except Exception as e:
        print(f"Error: {e}")


def get_video_attributes():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, PlaylistURL FROM playlist")
    for playlist_id, url in cursor.fetchall():
        playlist = PyTubePlaylist(url)
        counter = 0
        for urls in playlist.video_urls:
            youtubevideoid = extract_youtube_id(urls)
            # Check if the video is already grabbed
            cursor.execute("SELECT COUNT(*) AS records FROM videos WHERE YoutubeId = ?", (youtubevideoid,))
            try:
                query = cursor.fetchone()[0]
            except:
                query = 0
            if query == 0:
                print(youtubevideoid)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        # Grab YouTube metadata
                        YouTubeMeta = ydl.extract_info(urls, download=False)
                        title = YouTubeMeta.get('title')
                        #artist = split_text(title)
                        # Grab MusicBrainz metadata
                        try:
                            artist_data = search_recordings_by_artist(title)
                            #MusicBrainz = musicbrainzngs.search_artists(artist=artist)['artist-list'][0]
                        except Exception as e:
                            print(f"Error: {e}")
                        created_on = datetime.now(timezone.utc).isoformat()
                        cursor.execute("""
                            INSERT INTO videos (YoutubeId, VideoTitle, MusicBrainzId, MusicBrainzArtist , CreatedOn)
                            VALUES (?, ?, ?, ?, ?)
                        """, (youtubevideoid, title, artist_data["id"], artist_data["name"], created_on))
                        counter += 1
                    except Exception as e:
                        print(f"Error retrieving metadata: {e}")
                #print("Counter: ", counter)
                cursor.execute("UPDATE playlist SET Populated = ? WHERE ID = ?", (counter, playlist_id))
    conn.commit()
    conn.close()


def update_playlists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, PlaylistURL FROM playlist")
    for playlist_id, url in cursor.fetchall():
        try:
            playlist = PyTubePlaylist(url)
            song_count = len(playlist.video_urls)
            cursor.execute("UPDATE playlist SET Songs = ? WHERE ID = ?", (song_count, playlist_id))
        except Exception as e:
            print(f"Failed to update playlist {url}: {e}")
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("UPDATE config SET Value = ? WHERE Name = 'LastRun'", (now_str,))
    conn.commit()
    conn.close()
    get_video_attributes()

def background_updater():
    while True:
        update_playlists()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Value FROM config WHERE Name = 'ScheduledRun'")
        interval = int(cursor.fetchone()[0])
        conn.close()
        time.sleep(interval)

@app.route('/', methods=['GET'])
def index():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM playlist")
    playlists = cursor.fetchall()
    cursor.execute("SELECT Value FROM config WHERE Name = 'ScheduledRun'")
    scheduled_run = cursor.fetchone()[0]
    cursor.execute("SELECT Value FROM config WHERE Name = 'LastRun'")
    last_run = cursor.fetchone()[0]
    try:
        last_run_dt = datetime.fromisoformat(last_run)
        next_run_dt = last_run_dt + timedelta(seconds=int(scheduled_run))
        next_run = next_run_dt.isoformat()
    except:
        next_run = "Unknown"
    conn.close()
    return render_template_string(HTML_TEMPLATE, playlists=playlists, scheduled_run=scheduled_run, message=None, next_run=next_run, last_run=last_run)

@app.route('/add', methods=['POST'])
def add_playlist():
    playlist_url = request.form['playlist_url'].strip()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM playlist WHERE PlaylistURL = ?", (playlist_url,))
    if cursor.fetchone():
        cursor.execute("SELECT * FROM playlist")
        playlists = cursor.fetchall()
        cursor.execute("SELECT Value FROM config WHERE Name = 'ScheduledRun'")
        scheduled_run = cursor.fetchone()[0]
        cursor.execute("SELECT Value FROM config WHERE Name = 'LastRun'")
        last_run = cursor.fetchone()[0]
        conn.close()
        try:
            last_run_dt = datetime.fromisoformat(last_run)
            next_run = (last_run_dt + timedelta(seconds=int(scheduled_run))).isoformat()
        except:
            next_run = "Unknown"
        return render_template_string(HTML_TEMPLATE, playlists=playlists, scheduled_run=scheduled_run, message="Playlist URL already added.", next_run=next_run, last_run=last_run)
    try:
        playlist = PyTubePlaylist(playlist_url)
        title = playlist.title
        song_count = len(playlist.video_urls)
    except Exception as e:
        title = "Unknown Title"
        song_count = 0

    created_on = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO playlist (PlaylistURL, PlaylistTitle, Songs, Populated, CreatedOn)
        VALUES (?, ?, ?, ?, ?)
    """, (playlist_url, title, song_count, '', created_on))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/manual_run', methods=['POST'])
def manual_run():
    update_playlists()
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete_playlist():
    playlist_id = request.form.get('playlist_id')
    if playlist_id:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist WHERE ID = ?", (playlist_id,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/set_schedule', methods=['POST'])
def set_schedule():
    new_value = request.form.get('scheduled_run', '14400')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE config SET Value = ? WHERE Name = 'ScheduledRun'", (new_value,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/playlists', methods=['GET'])
def api_playlists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, PlaylistURL, PlaylistTitle, Songs, Populated, CreatedOn FROM playlist")
    rows = cursor.fetchall()
    conn.close()
    # Convert rows to list of dicts for JSON
    playlists = []
    for row in rows:
        playlists.append({
            'ID': row[0],
            'PlaylistURL': row[1],
            'PlaylistTitle': row[2],
            'Songs': row[3],
            'Populated': row[4],
            'CreatedOn': row[5]
        })
    return jsonify(playlists)

@app.route('/api/artists', methods=['GET'])
def api_videos():
    connapi = sqlite3.connect(db_path)
    cursorapi = connapi.cursor()
    cursorapi.execute("SELECT DISTINCT MusicBrainzId, MusicBrainzArtist FROM videos WHERE MusicBrainzId IS NOT NULL")
    rows = cursorapi.fetchall()
    connapi.close()
    # Convert rows to list of dicts for JSON
    artists = []
    for row in rows:
        artists.append({
            'MusicBrainzId': row[0],
            'MusicBrainzArtist': row[1]
        })
    return jsonify(artists)

@app.route('/api/config', methods=['GET'])
def api_config():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Name, Value, Description FROM config")
    rows = cursor.fetchall()
    conn.close()
    configs = []
    for row in rows:
        configs.append({
            'ID': row[0],
            'Name': row[1],
            'Value': row[2],
            'Description': row[3]
        })
    return jsonify(configs)

@app.route('/api/videos', methods=['GET'])
def api_videos_all():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT ID, YoutubeId, VideoTitle, MusicBrainzId, MusicBrainzArtist, CreatedOn FROM videos")
    rows = cursor.fetchall()
    conn.close()
    videos = []
    for row in rows:
        videos.append({
            'ID': row[0],
            'YoutubeId': row[1],
            'VideoTitle': row[2],
            'MusicBrainzId': row[3],
            'MusicBrainzArtist': row[4],
            'CreatedOn': row[5]
        })
    return jsonify(videos)


# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouPAL</title>
</head>
<body>
    <h1>YouTube Playlist Artist Lister</h1>
    {% if message %}<p><strong>{{ message }}</strong></p>{% endif %}
    <form method="post" action="/add">
        <input type="text" name="playlist_url" placeholder="YouTube Playlist URL" required>
        <button type="submit">Add</button>
    </form>
    <form method="post" action="/set_schedule">
        <input type="number" name="scheduled_run" value="{{ scheduled_run }}" placeholder="Scheduled Run (seconds)" required>
        <button type="submit">Set</button>
    </form>
    <p>Next Run: {{ next_run }}</p>
    <p>Last Run: {{ last_run }}</p>
    <form method="post" action="/manual_run">
        <button type="submit">Run</button>
    </form>
    <form method="post" action="/delete">
        <table border="1">
            <tr><th>Select</th><th>ID</th><th>Playlist URL</th><th>Playlist Title</th><th>Songs</th><th>Populated</th><th>Created On</th></tr>
            {% for row in playlists %}
            <tr>
                <td><input type="radio" name="playlist_id" value="{{ row[0] }}"></td>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td>{{ row[5] }}</td>
            </tr>
            {% endfor %}
        </table>
        <button type="submit">Delete</button>
    </form>
    <form method="get" action="/">
        <button type="submit">Refresh</button>
    </form>
</body>
</html>
'''


# --- Entry Point ---
if __name__ == '__main__':
    port = 8687
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port specified, using default 8687")

    threading.Thread(target=background_updater, daemon=True).start()
    app.run(debug=True, port=port)
