from pathlib import Path
from typing import Optional, Tuple
import re

_JUNK_PAREN_RE = re.compile(
    r"""
    \s*                # leading space
    \(                 # opening parenthesis
    \s*
    (?:official\s+)?   # optional "official"
    (?:audio|video|lyrics|visualizer)  # junk keywords
    \s*
    \)                 # closing parenthesis
    \s*                # trailing space
    """,
    re.IGNORECASE | re.VERBOSE,
)

def extract_track_title(
    filename: str,
    artist: Optional[str] = None,
) -> Tuple[str, str]:
    stem = Path(filename).stem

    parts = stem.split("-", 1)
    track_no = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""

    if artist:
        title = re.sub(
            rf"^{re.escape(artist)}\s*-\s*",
            "",
            title,
            flags=re.IGNORECASE,
        )

    title = _JUNK_PAREN_RE.sub("", title)

    title = re.sub(r"\s{2,}", " ", title).strip()

    return track_no, title
