from pathlib import Path
from tui import AlbumSelector

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Discography downloader")
    parser.add_argument("handle", type=str, help="YouTube artist handle")
    parser.add_argument("--artist", type=str, help="Artist Name")
    parser.add_argument("--format", type=str, default="mp3",
                        choices=["mp3", "webm", "flac", "m4a"], help="Specify the file format")
    parser.add_argument("--output", type=str, default=".", help="Output path")
    parser.add_argument("--cookies", type=str, help="Path to cookie file or browser name (for downloading age restricted videos)")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    AlbumSelector(handle=args.handle, artist=args.artist, output_dir=str(output_path.resolve()), target_format=args.format).run()



if __name__ == "__main__":
    main()
