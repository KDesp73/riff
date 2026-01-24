import os
import subprocess
from typing import List, Optional


def convert_audio(
    input_file: str,
    output_format: str = "mp3",
    output_dir: Optional[str] = None,
    bitrate: str = "192k"
) -> str:
    """
    Converts a single audio/video file to the specified audio format using ffmpeg.

    :param input_file: Path to the input file (e.g., file.webm)
    :param output_format: Output audio format ('mp3', 'wav', 'flac', etc.)
    :param output_dir: Directory to save the converted file. Defaults to same as input.
    :param bitrate: Audio bitrate (only used for lossy formats like mp3)
    :return: Path to the converted file
    """
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{base_name}.{output_format}")
    else:
        output_file = os.path.join(os.path.dirname(input_file), f"{base_name}.{output_format}")

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",  # overwrite without asking
        "-i", input_file,
    ]

    # Use bitrate only for mp3/aac/ogg
    if output_format.lower() in ("mp3", "aac", "ogg", "m4a"):
        cmd += ["-b:a", bitrate]

    cmd.append(output_file)

    # Run conversion
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{result.stderr}")

    return output_file


def batch_convert(
    files: List[str],
    output_format: str = "mp3",
    output_dir: Optional[str] = None,
    bitrate: str = "192k"
) -> List[str]:
    """
    Convert a list of files.

    :param files: List of file paths
    :param output_format: Output audio format
    :param output_dir: Output directory
    :param bitrate: Audio bitrate for lossy formats
    :return: List of converted file paths
    """
    converted = []
    for f in files:
        try:
            out_file = convert_audio(f, output_format, output_dir, bitrate)
            converted.append(out_file)
            print(f"Converted: {f} -> {out_file}")
        except Exception as e:
            print(f"Failed to convert {f}: {e}")
    return converted


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert audio/video files to another audio format.")
    parser.add_argument("files", nargs="+", help="Input files (e.g., .webm, .mp4)")
    parser.add_argument("-f", "--format", default="mp3", help="Output format (mp3, wav, flac, etc.)")
    parser.add_argument("-o", "--outdir", help="Output directory")
    parser.add_argument("-b", "--bitrate", default="192k", help="Bitrate for lossy formats (mp3, aac, etc.)")

    args = parser.parse_args()

    batch_convert(args.files, args.format, args.outdir, args.bitrate)

