"""Command-line interface for Audio Extractor."""
import os
import sys
import argparse
from .downloader import build_ydl_opts, fetch_info, run_download
from .metadata import FORMAT_CODEC_MAP
from .utils import check_dependencies

def cli_progress_hook(d: dict) -> None:
    """Progress hook for CLI mode - prints download progress."""
    status = d.get("status")
    if status == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed") or 0
        eta = d.get("eta") or 0
        pct = (downloaded / total * 100) if total else 0
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "#" * filled + "-" * (bar_len - filled)
        speed_s = f"{speed/1024/1024:.1f} MB/s" if speed else "?"
        eta_s = f"{eta}s" if eta else "?"
        print(f"\r  [{bar}] {pct:5.1f}%  {speed_s}  ETA {eta_s}   ", end="", flush=True)
    elif status == "finished":
        print(f"\r  Done — converting...{' '*30}")
    elif status == "error":
        print("\n  Download error")

def run_headless(
    url: str,
    output_dir: str,
    fmt: str,
    quality: str,
    no_playlist: bool,
) -> None:
    """Run download in headless/CLI mode.

    Args:
        url: URL to download from.
        output_dir: Directory to save the file.
        fmt: Audio format.
        quality: Quality setting.
        no_playlist: If True, download only single track.
    """
    import yt_dlp
    check_dependencies(raise_on_missing=False)
    opts = build_ydl_opts(output_dir, fmt, quality, no_playlist,
                          progress_hook=cli_progress_hook)
    print(f"\nExtracting audio")
    print(f"   URL    : {url}")
    print(f"   Format : {fmt.upper() if fmt != 'best' else 'Best native'}")
    print(f"   Output : {os.path.expanduser(output_dir)}\n")
    try:
        info = fetch_info(url, opts)
        title = info.get("title", "Unknown")
        uploader = (info.get("artist") or info.get("uploader")
                    or info.get("channel") or "Unknown artist")
        duration = info.get("duration")
        dur_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "?"
        print(f"   Title  : {title}")
        print(f"   Artist : {uploader}")
        print(f"   Length : {dur_str}\n")
        run_download(url, opts)
        print("\nDone!\n")
    except yt_dlp.utils.DownloadError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="Download audio at the highest quality from any URL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=True,
    )
    parser.add_argument("url", nargs="?", default=None,
                        help="URL to download (omit to open GUI)")
    parser.add_argument("--ui", action="store_true",
                        help="Force open the graphical interface")
    parser.add_argument("--format", "-f",
                        choices=list(FORMAT_CODEC_MAP.keys()),
                        default="best")
    parser.add_argument("--quality", "-q", default="0")
    parser.add_argument("--output", "-o",
                        default=os.path.expanduser("~/.config/audio_extractor"))
    parser.add_argument("--no-playlist", action="store_true", default=True)
    return parser
