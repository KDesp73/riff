#!/usr/bin/env python3

from pathlib import Path
from tui import AlbumSelector
from metadata import set_metadata
from converter import convert_audio, batch_convert
import argparse

def browse(args):
    """Launch TUI to select and download albums."""
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    AlbumSelector(
        handle=args.handle,
        artist=args.artist or args.handle,
        output_dir=str(output_path.resolve()),
        target_format=args.format,
        cookies=args.cookies
    ).run()


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
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--artist", type=str, help="Artist name")
    parser.add_argument("--format", type=str, default="mp3",
                        choices=["mp3", "webm", "flac", "m4a"], help="Target file format")
    parser.add_argument("--input", type=str, help="Input path for metadata/conversion")
    parser.add_argument("--output", type=str, default=".", help="Output directory")

    subparsers = parser.add_subparsers(title="commands", dest="command")

    browse_parser = subparsers.add_parser("browse", help="Select and download albums interactively")
    browse_parser.add_argument("--handle", required=True, type=str, help="YouTube artist handle")
    browse_parser.add_argument("--cookies", type=str, help="Path to cookie file or browser name")

    subparsers.add_parser("metadata", help="Apply metadata to files")
    subparsers.add_parser("convert", help="Convert files to another format")

    args = parser.parse_args()

    if args.version:
        print("riff v1.0.0")
        return

    if args.command == "browse":
        browse(args)
    elif args.command == "metadata":
        metadata(args)
    elif args.command == "convert":
        convert(args)


if __name__ == "__main__":
    main()
