"""Download logic using yt-dlp."""

import os
import yt_dlp
from typing import Any, Callable, Optional

def build_ydl_opts(
    output_dir: str,
    format: str,
    quality: str,
    no_playlist: bool,
    progress_hook: Optional[Callable[[dict], None]] = None,
    outtmpl: Optional[str] = None,
) -> dict[str, Any]:
    """Build yt-dlp options dictionary.

    Args:
        output_dir: Directory to save downloaded files.
        format: Audio format (best, flac, mp3, etc.).
        quality: Quality setting (0-9 for mp3, kbps for aac/opus).
        no_playlist: If True, download only single track.
        progress_hook: Optional callback for progress updates.
        outtmpl: Optional output template override.

    Returns:
        Dictionary of yt-dlp options.
    """
    output_dir = os.path.expanduser(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    audio_format = "bestaudio"

    post_processors = []
    if format != "best":
        post_processors.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": format if format != "vorbis" else "vorbis",
            "preferredquality": quality,
        })
    post_processors.append({"key": "FFmpegMetadata"})
    embed_thumb_formats = {"mp3", "m4a", "aac", "best", "flac"}
    if format in embed_thumb_formats:
        post_processors.append({"key": "EmbedThumbnail"})

    opts = {
        "format": audio_format,
        "outtmpl": outtmpl or os.path.join(
            output_dir, "%(artist,uploader)s - %(title)s.%(ext)s"
        ),
        "postprocessors": post_processors,
        "writethumbnail": format in embed_thumb_formats,
        "embedthumbnail": format in embed_thumb_formats,
        "addmetadata": True,
        "progress_hooks": [progress_hook] if progress_hook else [],
        "noplaylist": no_playlist,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": True,
        "verbose": False,
        "retries": 5,
        "fragment_retries": 5,
        "sleep_interval": 1,
        "max_sleep_interval": 3,
    }
    return opts

def fetch_info(url: str, ydl_opts: dict) -> dict:
    """Fetch video/audio info without downloading."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False) or {}

def run_download(url: str, ydl_opts: dict) -> None:
    """Download audio from URL using yt-dlp."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
