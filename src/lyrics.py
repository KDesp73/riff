import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from cache import Cache

class LyricsDownloader:
    """Fetches lyrics from MusixMatch API."""
    def __init__(self, artist: str, title: str, download_path: str, use_old: bool = False, fallback: bool = True):
        if not title or not artist or not download_path:
            raise ValueError("Missing required parameters")
        self.artist = artist
        self.title = title
        self.download_path = download_path
        if not use_old:
            self.token = self._load_or_fetch_token()
        self.cache = Cache("~/.cache/riff/lyrics.cache", ttl=60 * 60 * 24 * 7)
        self.ROOT_URL = "https://apic-desktop.musixmatch.com/ws/1.1/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            "Authority": "apic-desktop.musixmatch.com"
        })
        self.lyrics: dict = {}

    def _load_or_fetch_token(self):
            """Manages token caching and refreshing."""

            cachedToken = self.cache.get("token")
            if cachedToken:
                data = json.loads(cachedToken)
                if data['expires_at'] > time.time():
                    return data['token']

            params = {"app_id": "web-desktop-app-v1.0", "user_language": "en", "t": int(time.time() * 1000)}
            res = self.session.get(f"{self.ROOT_URL}token.get", params=params).json()
            
            token = res["message"]["body"]["user_token"]

            self.cache.set("token", json.dumps({
                "token": token,
                "expires_at": time.time() + 600
            }))
            return token

    def fetch_lyrics_metadata(self, search_term: str) -> dict:
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


    def get_lyrics_legacy(self, query: str) -> dict:
        if not query:
            return {
                "status": 400,
                "message": "Song name query is required!",
            }

        res = self.fetch_lyrics_metadata(query)

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

    def get_synced_lyrics(self) -> dict:

        if not time or not self.artist:
            return {
                "status": 400,
                "message": "Song title and artist name are required!",
            }

        search_params = {
            "q_track":  self.title,
            "q_artist": self.artist,
            "f_has_lyrics": 1,
            "usertoken": self.token,
            "app_id": "web-desktop-app-v1.0"
        }
        
        search_res = self.session.get(f"{self.ROOT_URL}track.search", params=search_params).json()
        tracks = search_res["message"]["body"].get("track_list", [])

        if not tracks:
            return {
                "status": 404,
                "message": f"No lyrics found for '{self.title}' by {self.artist}",
            }

        track_id = tracks[0]["track"]["track_id"]
            
        lrc_params = {
            "track_id": track_id,
            "subtitle_format": "lrc",
            "usertoken": self.token,
            "app_id": "web-desktop-app-v1.0"
        }
        
        lrc_res = self.session.get(f"{self.ROOT_URL}track.subtitle.get", params=lrc_params).json()
        lrc_content = lrc_res["message"]["body"]["subtitle"]["subtitle_body"]

        return {
            "status": 200,
            "lyrics": lrc_content,
        }
    
    def get_lyrics(self) -> dict:
        if self.use_old:
            return self.get_lyrics_legacy(self.title, f" by {self.artist}" if self.artist else "")
        else:
            lyrcs = self.get_synced_lyrics()
            if lyrcs.get("status") == 200:
                return lyrcs
            else:
                if self.fallback:
                    return self.get_lyrics_legacy(self.title, f" by {self.artist}" if self.artist else "")
                else:
                    return {
                        "status": 404,
                        "message": f"No lyrics found for '{self.title}' by {self.artist}",
                    }
                
    def download_lyrics(self) -> dict:
        lyrics_data = self.get_lyrics()

        if lyrics_data.get("status") == 200:
            lyrics_file = self.download_path.with_suffix(".lrc")
            lyrics_file.write_text(lyrics_data.get("lyrics"), encoding="utf-8")
            return {
                "status": 200,
                "message": f"Lyrics saved: {lyrics_file.name}",
            }
        
        return lyrics_data
        