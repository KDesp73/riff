import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


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
