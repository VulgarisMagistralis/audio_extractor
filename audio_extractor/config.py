"""Configuration management for Audio Extractor."""
import os
import json
import pathlib

_CONFIG_PATH = pathlib.Path(
    os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
) / "audio_extractor" / "settings.json"

_DEFAULTS = {
    "bg": "#000000",
    "accent": "#fffb1b",
    "fg": "#ffffff",
    "fg_dim": "#7a7a88",
    "font_size": 11,
    "output_dir": "~/Downloads/audio",
    "fmt": "best",
}

def load_config() -> dict:
    """Load configuration from settings.json or return defaults."""
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text())
            return {**_DEFAULTS, **data}
    except Exception:
        pass
    return dict(_DEFAULTS)

def save_config(cfg: dict) -> None:
    """Save configuration to settings.json."""
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as e:
        print(f"[config] save failed: {e}")

