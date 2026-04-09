"""Utility functions for Audio Extractor."""

import shutil
import sys

def check_dependencies(raise_on_missing: bool = False) -> bool:
    """Check if required dependencies (yt-dlp, ffmpeg) are available.

    Args:
        raise_on_missing: If True, raise RuntimeError on missing deps.

    Returns:
        True if all dependencies are available.

    Raises:
        RuntimeError: If raise_on_missing is True and dependencies are missing.
    """
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp  ->  pip install yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg  ->  brew install ffmpeg  /  sudo apt install ffmpeg")
    if missing:
        msg = "Missing dependencies:\n" + "\n".join(f"  * {m}" for m in missing)
        if raise_on_missing:
            raise RuntimeError(msg)
        print("ERROR  " + msg)
        sys.exit(1)
    return True
