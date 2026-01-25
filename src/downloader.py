from typing import List, Callable, Dict, Optional
from yt_dlp import YoutubeDL
from cache import Cache

cache = Cache("~/.cache/riff.cache")

def get_artist_albums(artist: str) -> List[Dict[str, str]]:
    cache_key = f"artist_albums:{artist}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
    }

    releases_url = f"https://www.youtube.com/@{artist}/releases"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(releases_url, download=False)
        entries = info.get("entries", [])

    result = [
        {"title": e["title"], "url": e["url"]}
        for e in entries
        if e.get("title") and e.get("url")
    ]

    cache.set(cache_key, result)
    return result


def get_album_tracks(album_url: str) -> List[Dict[str, str]]:
    cache_key = f"album_tracks:{album_url}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(album_url, download=False)
        entries = info.get("entries", [])

    result = [
        {"title": e["title"], "url": e["url"]}
        for e in entries
        if e.get("url")
    ]

    cache.set(cache_key, result)
    return result
