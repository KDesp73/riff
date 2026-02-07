import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from cache import Cache

cache = Cache("~/.cache/riff/lyrics.cache", ttl=60 * 60 * 24 * 7)
ROOT_URL = "https://apic-desktop.musixmatch.com/ws/1.1/"
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Authority": "apic-desktop.musixmatch.com"
})

def _load_or_fetch_token():
        """Manages token caching and refreshing."""

        cachedToken = cache.get("token")
        if cachedToken:
            data = json.loads(cachedToken)
            if data['expires_at'] > time.time():
                return data['token']

        params = {"app_id": "web-desktop-app-v1.0", "user_language": "en", "t": int(time.time() * 1000)}
        res = session.get(f"{ROOT_URL}token.get", params=params).json()
        
        token = res["message"]["body"]["user_token"]

        cache.set("token", json.dumps({
            "token": token,
            "expires_at": time.time() + 600
        }))
        return token

def fetch_lyrics_metadata(search_term: str) -> dict:
    try:
        url = (
            "https://genius.com/api/search/multi"
            f"?per_page=1&q={quote(search_term)}"
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://genius.com/",
            "Origin": "https://genius.com",
        }

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        sections = data.get("response", {}).get("sections", [])
        if len(sections) < 2 or not sections[1].get("hits"):
            return {"status": 500, "message": "Song not found"}

        result = sections[1]["hits"][0]["result"]

        return {
            "status": 200,
            "url": result.get("url"),
            "album": result.get("full_title"),
            "thumbnail": result.get("header_image_url"),
            "artist": result.get("primary_artist", {}).get("name"),
            "release_date": result.get("release_date_for_display"),
        }

    except Exception as e:
        return {"status": 500, "message": str(e)}


def get_lyrics(query: str) -> dict:
    if not query:
        return {
            "status": 400,
            "message": "Song name query is required!",
        }

    res = fetch_lyrics_metadata(query)

    if res.get("status") != 200 or not res.get("url"):
        return res

    try:
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        html = requests.get(res["url"], headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        containers = soup.select("[data-lyrics-container]")
        lyrics_blocks = []

        for c in containers:
            for br in c.find_all("br"):
                br.replace_with("\n")
            lyrics_blocks.append(c.get_text())

        lyrics = "\n".join(lyrics_blocks).strip()

        if not lyrics:
            return {
                "status": 500,
                "message": f"Unable to find song: {query}",
            }

        return {
            "status": 200,
            "url": res.get("url"),
            "album": res.get("album"),
            "artist": res.get("artist"),
            "release_date": res.get("release_date"),
            "thumbnail": res.get("thumbnail"),
            "lyrics": lyrics,
        }

    except Exception as e:
        return {
            "status": 500,
            "message": str(e),
        }

def get_synced_lyrics(title: str, artist: str) -> dict:

    if not time or not artist:
        return {
            "status": 400,
            "message": "Song title and artist name are required!",
        }

    token = _load_or_fetch_token()
    search_params = {
        "q_track": title,
        "q_artist": artist,
        "f_has_lyrics": 1,
        "usertoken": token,
        "app_id": "web-desktop-app-v1.0"
    }
    
    search_res = session.get(f"{ROOT_URL}track.search", params=search_params).json()
    tracks = search_res["message"]["body"].get("track_list", [])

    if not tracks:
        return {
            "status": 404,
            "message": f"No lyrics found for '{title}' by {artist}",
        }

    track_id = tracks[0]["track"]["track_id"]
        
    lrc_params = {
        "track_id": track_id,
        "subtitle_format": "lrc",
        "usertoken": token,
        "app_id": "web-desktop-app-v1.0"
    }
    
    lrc_res = session.get(f"{ROOT_URL}track.subtitle.get", params=lrc_params).json()
    lrc_content = lrc_res["message"]["body"]["subtitle"]["subtitle_body"]

    return {
        "status": 200,
        "lyrics": lrc_content,
    }