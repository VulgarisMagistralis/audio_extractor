"""Tests for audio_extractor.cli."""
import argparse
import sys
from unittest.mock import patch, MagicMock

from audio_extractor.cli import create_parser, cli_progress_hook


class TestCreateParser:
    """Tests for create_parser."""

    def test_returns_argument_parser(self):
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parses_url(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com/video"])
        assert args.url == "https://example.com/video"

    def test_default_format_is_best(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.format == "best"

    def test_parses_mp3_format(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com", "--format", "mp3"])
        assert args.format == "mp3"

    def test_parses_short_format_flag(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com", "-f", "flac"])
        assert args.format == "flac"

    def test_default_quality_is_0(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.quality == "0"

    def test_parses_quality(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com", "-q", "9"])
        assert args.quality == "9"

    def test_ui_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--ui"])
        assert args.ui is True

    def test_no_url_sets_ui(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.url is None

    def test_rejects_invalid_format(self):
        parser = create_parser()
        try:
            parser.parse_args(["https://example.com", "-f", "wma"])
            raise AssertionError("Should have raised SystemExit")
        except SystemExit:
            pass

    def test_parses_output_dir(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com", "-o", "/tmp/music"])
        assert args.output == "/tmp/music"

    def test_parses_no_playlist(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com", "--no-playlist"])
        assert args.no_playlist is True


class TestCliProgressHook:
    """Tests for cli_progress_hook."""

    def test_downloading_status_prints_percent(self, capsys):
        hook_data = {
            "status": "downloading",
            "total_bytes": 1000000,
            "downloaded_bytes": 500000,
            "speed": 1048576,
            "eta": 10,
        }
        cli_progress_hook(hook_data)
        out = capsys.readouterr()
        assert "50.0%" in out.out

    def test_finished_status_prints_done(self, capsys):
        cli_progress_hook({"status": "finished"})
        out = capsys.readouterr()
        assert "Done" in out.out

    def test_error_status_prints_error(self, capsys):
        cli_progress_hook({"status": "error"})
        out = capsys.readouterr()
        assert "error" in out.out.lower()

    def test_downloading_zero_total_does_not_crash(self):
        hook_data = {
            "status": "downloading",
            "total_bytes": 0,
            "downloaded_bytes": 0,
            "speed": 0,
            "eta": 0,
        }
        cli_progress_hook(hook_data)
