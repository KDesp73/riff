from typing import List, Dict
from collections import Counter
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

from yt_dlp import YoutubeDL
from collections import Counter
from typing import List, Dict

def search_artist(query: str) -> List[Dict[str, str]]:
    """
    Search for an artist on YouTube by exact handle first, then fallback to general search.
    Returns a list of dicts: {"handle": str, "artist": str}.
    """
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
    }

    found: List[Dict[str, str]] = []

    # Try exact handle first
    handle = "".join(query.split(" "))
    exact_url = f"https://www.youtube.com/@{handle}/releases"
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(exact_url, download=False)
            if info and info.get("entries"):
                found.append({"handle": handle, "artist": query})
                return found
    except Exception:
        pass

    # Fallback to general search
    search_url = f"ytsearch20:{query}"  # top 20 results
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get("entries", [])

            # Count channel appearances
            channels = [e.get("channel") for e in entries if e.get("channel")]
            channel_counts = Counter(channels)

            # Sort channels by frequency
            sorted_channels = [c for c, _ in channel_counts.most_common()]

            for channel_name in sorted_channels:
                # Get first entry for this channel to extract artist title
                entry = next((e for e in entries if e.get("channel") == channel_name), None)
                if entry:
                    handle = entry.get("channel").replace("@", "")
                    artist_name = entry.get("uploader") or entry.get("title") or query
                    found.append({"handle": handle, "artist": artist_name})

    except Exception:
        pass

    if not found:
        found.append({"handle": "", "artist": f"No results for '{query}'"})

    return found
