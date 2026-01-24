from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from pathlib import Path

def set_metadata(file_path, metadata: dict):
    """
    Set metadata for a file in a simplified way.
    Works for MP3 (ID3v2.3 + ID3v1.1), FLAC, and MP4/M4A.

    metadata = {
        "artist": "Hozier",
        "album": "Wasteland, Baby!",
        "title": "Eat Your Young",
        "tracknumber": "1",
        "date": "2019",
        "genre": "Alternative",
    }
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower().lstrip(".")

    if ext == "mp3":
        audio = EasyID3(file_path)
        for key, value in metadata.items():
            audio[key] = value
        audio.save(v2_version=3)

    elif ext == "flac":
        audio = FLAC(file_path)
        for key, value in metadata.items():
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
        for key, value in metadata.items():
            if key in mapping:
                audio[mapping[key]] = value
        audio.save()

    else:
        print(f"Unsupported file type for metadata: {file_path}")
