#!/usr/bin/env python3

from pathlib import Path

from src.tui.app import RiffApp
from tui import RiffApp, DownloaderScreen
from metadata import set_metadata
from converter import convert_audio
import argparse

def metadata(args):
    """Apply metadata to a file or directory of files."""
    if not args.input:
        print("Error: --input is required for metadata")
        return

    artist = args.artist
    input_path = Path(args.input)

    if input_path.is_dir():
        files = list(input_path.glob("*.mp3"))
        for path in files:
            filename = path.stem
            track_number = filename.split("-")[0].strip()
            title = [part.strip() for part in filename.split("-")][-1]
            set_metadata(path, {
                "artist": artist,
                "album": str(path.parent.name),
                "title": title,
                "tracknumber": track_number,
            })
    else:
        set_metadata(input_path, {
            "artist": artist,
            "album": str(input_path.parent.name),
            "title": input_path.stem,
            "tracknumber": "1",
        })

def convert(args):
    """Convert a file or directory of files to a target format in-place."""
    if not args.input:
        print("Error: --input is required for convert")
        return

    input_path = Path(args.input)
    target_format = args.format

    if input_path.is_dir():
        files = [f for f in input_path.glob("*.webm") if f.is_file()]
        for file in files:
            out_file = file
            if target_format != "webm":
                print(f"Converting {file.name} → {target_format}")
                out_file = Path(convert_audio(str(file), target_format, str(file.parent)))
                file.unlink()  # remove original webm
    else:
        file = input_path
        out_file = file
        if target_format != "webm":
            print(f"Converting {file.name} → {target_format}")
            out_file = Path(convert_audio(str(file), target_format, str(file.parent)))
            file.unlink()


def main():
    parser = argparse.ArgumentParser(description="Discography downloader CLI")
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    parser.add_argument("--artist", type=str, help="Artist name")
    parser.add_argument("--format", type=str, default="mp3",
                        choices=["mp3", "webm", "flac", "m4a"], help="Target file format")
    parser.add_argument("--input", type=str, help="Input path for metadata/conversion")
    parser.add_argument("--output", type=str, default=".", help="Output directory")
    parser.add_argument("--handle", type=str, help="YouTube artist handle")
    parser.add_argument("--cookies", type=str, help="Path to cookie file or browser name")
    parser.add_argument("--lyrics", type=bool, help="Download lyrics?", default=False) 

    subparsers = parser.add_subparsers(title="commands", dest="command")
    subparsers.add_parser("metadata", help="Apply metadata to files")
    subparsers.add_parser("convert", help="Convert files to another format")

    args = parser.parse_args()

    if args.version:
        print("riff v1.1.0")
        return

    if args.command == "metadata":
        metadata(args)
    elif args.command == "convert":
        convert(args)

    RiffApp().run()


if __name__ == "__main__":
    main()
