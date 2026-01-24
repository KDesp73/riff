import queue
import threading
from typing import List, Callable, Dict, Optional
from yt_dlp import YoutubeDL


def get_artist_albums(artist: str) -> List[Dict[str, str]]:
    """
    Get the list of albums/releases for a YouTube artist.
    """
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
    }
    releases_url = f"https://www.youtube.com/@{artist}/releases"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(releases_url, download=False)
        entries = info.get("entries", [])

    return [
        {"title": e["title"], "url": e["url"]}
        for e in entries
        if e.get("title") and e.get("url")
    ]


def get_album_tracks(album_url: str) -> List[str]:
    """
    Returns the list of track URLs for a single album.
    """
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(album_url, download=False)
        entries = info.get("entries", [])
    return [e["url"] for e in entries if e.get("url")]


def download_albums(
    urls: List[str],
    progress_callback: Callable[[str], None],
    cookies: Optional[str] = None,
    per_file_timeout: int = 300,  # seconds
):
    """
    Downloads a list of album URLs with optional browser cookies for age-restricted content.
    If a file download hangs longer than `per_file_timeout`, it will be skipped.
    Reports progress via the callback.
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
        "ratelimit": 2_000_000,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,
        "progress_hooks": [],
        "noplaylist": False,
    }

    if cookies:
        if cookies.lower() in ["chrome", "firefox", "edge"]:
            ydl_opts["cookies_from_browser"] = (cookies.lower(),)
        else:
            ydl_opts["cookiefile"] = cookies

    def ydl_hook(d):
        filename = d.get("filename", "")
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            progress_callback(f"⬇ {filename} {percent} {speed} ETA {eta}")
        elif d["status"] == "finished":
            progress_callback(f"✔ Finished: {filename}")

    ydl_opts["progress_hooks"] = [ydl_hook]

    def download_url(url):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            progress_callback(f"✅ Finished album: {url}")
        except Exception as e:
            progress_callback(f"⚠ Error downloading {url}: {e}")

    def worker():
        for url in urls:
            finished_event = threading.Event()
            result_queue = queue.Queue()

            def target():
                try:
                    download_url(url)
                finally:
                    finished_event.set()

            t = threading.Thread(target=target)
            t.start()

            # Wait for the file to finish or timeout
            if not finished_event.wait(timeout=per_file_timeout):
                progress_callback(f"⏱ Timeout, skipping: {url}")
                # Note: cannot safely kill yt_dlp thread; will continue in background
            t.join(0)  # Don't block indefinitely

        progress_callback("All downloads attempted ✔")

    threading.Thread(target=worker, daemon=True).start()
