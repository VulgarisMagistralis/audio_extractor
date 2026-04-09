"""Audio metadata and format handling."""

import re

FORMAT_CODEC_MAP = {
    "best": None,
    "flac": "flac",
    "wav": "pcm_s16le",
    "mp3": "libmp3lame",
    "aac": "aac",
    "opus": "libopus",
    "m4a": "aac",
    "vorbis": "libvorbis",
}

def safe_stem(name: str) -> str:
    """Sanitize a filename stem by removing invalid characters."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip().rstrip(".")[:180]
