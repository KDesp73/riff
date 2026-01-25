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
    per_album_timeout: int = 300,  # seconds
    output_template: Optional[str] = None,
):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template or "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
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
        status = d.get("status")
        if status == "downloading":
            pct = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            progress_callback(f"⬇ {filename} {pct} {speed} ETA {eta}")
        elif status == "finished":
            progress_callback(f"✔ Finished {filename}")

    ydl_opts["progress_hooks"] = [ydl_hook]

    def download_album(url):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            progress_callback(f"✅ Finished album: {url}")
        except Exception as e:
            progress_callback(f"⚠ Error downloading {url}: {e}")

    def album_worker(url):
        finished_event = threading.Event()

        def target():
            try:
                download_album(url)
            finally:
                finished_event.set()

        t = threading.Thread(target=target, daemon=True)
        t.start()

        if not finished_event.wait(timeout=per_album_timeout):
            progress_callback(f"⏱ Timeout, skipping album: {url}")
        # thread continues in background, but UI is not blocked

    for url in urls:
        threading.Thread(target=album_worker, args=(url,), daemon=True).start()
