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


def get_album_tracks(album_url: str) -> List[Dict[str, str]]:
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
    return [{"title": e["title"], "url": e["url"]} for e in entries if e.get("url")]
