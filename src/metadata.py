from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from pathlib import Path

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from pathlib import Path

def set_metadata(file_path, metadata: dict):
    """
    Set metadata for a file safely.
    Converts all values to strings, skips None.
    """
    ext = Path(file_path).suffix.lower()[1:]  # remove dot

    # Make a copy with only non-None string values
    clean_metadata = {k: str(v) for k, v in metadata.items() if v is not None}

    if ext == "mp3":
        try:
            audio = EasyID3(file_path)
        except Exception:
            # If no ID3 header exists, create one
            from mutagen.id3 import ID3
            audio = ID3()
            audio.save(file_path)
            audio = EasyID3(file_path)

        for key, value in clean_metadata.items():
            audio[key] = value
        audio.save(v2_version=4)  # optional: v2.4.0

    elif ext == "flac":
        audio = FLAC(file_path)
        for key, value in clean_metadata.items():
            audio[key] = value
        audio.save()
    elif ext in ("m4a", "mp4"):
        audio = MP4(file_path)
        mapping = {
            "title": "\xa9nam",
            "artist": "\xa9ART",
            "album": "\xa9alb",
            "tracknumber": "trkn",
            "date": "\xa9day",
            "genre": "\xa9gen",
        }
        for k, v in clean_metadata.items():
            if k in mapping:
                audio[mapping[k]] = v
        audio.save()
    else:
        print(f"Unsupported file type for metadata: {file_path}")
