"""Tests for audio_extractor.config."""
import json
import os
import tempfile
from unittest.mock import patch

from audio_extractor.config import load_config, save_config, _DEFAULTS


class TestLoadConfig:
    """Tests for load_config."""

    def test_returns_dict(self):
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_contains_defaults_when_file_missing(self, tmp_path):
        non_existent = tmp_path / "does_not_exist_dir" / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", non_existent):
            cfg = load_config()
        assert "bg" in cfg
        assert "accent" in cfg

    def test_default_bg_is_black(self, tmp_path):
        non_existent = tmp_path / "nope" / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", non_existent):
            cfg = load_config()
        assert cfg["bg"] == "#000000"

    def test_default_accent_is_yellow(self, tmp_path):
        non_existent = tmp_path / "nope2" / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", non_existent):
            cfg = load_config()
        assert cfg["accent"] == "#fffb1b"

    def test_returns_defaults_copy(self, tmp_path):
        non_existent = tmp_path / "nope3" / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", non_existent):
            cfg = load_config()
        assert cfg == _DEFAULTS
        cfg["bg"] = "#ffffff"
        assert _DEFAULTS["bg"] == "#000000"

    def test_user_values_override_defaults(self, tmp_path):
        file_path = tmp_path / "settings.json"
        file_path.write_text(json.dumps({"accent": "#ff0000"}))
        with patch("audio_extractor.config._CONFIG_PATH", file_path):
            cfg = load_config()
        assert cfg["accent"] == "#ff0000"
        assert cfg["bg"] == _DEFAULTS["bg"]

    def test_returns_defaults_on_json_decode_error(self, tmp_path):
        file_path = tmp_path / "settings.json"
        file_path.write_text("not valid json {{{")
        with patch("audio_extractor.config._CONFIG_PATH", file_path):
            cfg = load_config()
        assert cfg == _DEFAULTS


class TestSaveConfig:
    """Tests for save_config."""

    def test_creates_directory_and_file(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", nested):
            save_config({"bg": "#000000"})
        assert nested.exists()

    def test_writes_json(self, tmp_path):
        file_path = tmp_path / "settings.json"
        data = {"bg": "#123456", "fmt": "flac"}
        with patch("audio_extractor.config._CONFIG_PATH", file_path):
            save_config(data)
        parsed = json.loads(file_path.read_text())
        assert parsed == data

    def test_persists_across_loads(self, tmp_path):
        file_path = tmp_path / "settings.json"
        with patch("audio_extractor.config._CONFIG_PATH", file_path):
            save_config({"bg": "#abcdef"})
            cfg = load_config()
        assert cfg["bg"] == "#abcdef"

    def test_default_config_keys(self):
        assert "font_size" in _DEFAULTS
        assert _DEFAULTS["font_size"] == 11
        assert "output_dir" in _DEFAULTS