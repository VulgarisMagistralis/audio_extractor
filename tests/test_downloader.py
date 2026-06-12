"""Tests for audio_extractor.downloader."""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from audio_extractor.downloader import build_ydl_opts, fetch_info, run_download


class TestBuildYdlOpts:
    """Tests for build_ydl_opts."""

    def test_returns_dict(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert isinstance(opts, dict)

    def test_creates_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_dir = os.path.join(tmp, "newdir")
            build_ydl_opts(new_dir, "best", "0", False)
            assert os.path.isdir(new_dir)

    def test_default_format_is_bestaudio(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert opts["format"] == "bestaudio"

    def test_outtmpl_contains_artist_and_title(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert "%(artist,uploader)s" in opts["outtmpl"]
        assert "%(title)s" in opts["outtmpl"]

    def test_noplaylist_true(self):
        opts = build_ydl_opts("/tmp", "best", "0", True)
        assert opts["noplaylist"] is True

    def test_noplaylist_false(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert opts["noplaylist"] is False

    def test_no_post_processor_for_best(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        keys = [pp.get("key") for pp in opts["postprocessors"]]
        assert "FFmpegExtractAudio" not in keys

    def test_ffmpeg_extract_audio_added_for_mp3(self):
        opts = build_ydl_opts("/tmp", "mp3", "5", False)
        keys = [pp.get("key") for pp in opts["postprocessors"]]
        assert "FFmpegExtractAudio" in keys

    def test_ffmpeg_codec_set_for_mp3(self):
        opts = build_ydl_opts("/tmp", "mp3", "5", False)
        pp = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio")
        assert pp["preferredcodec"] == "mp3"

    def test_ffmpeg_codec_set_for_flac(self):
        opts = build_ydl_opts("/tmp", "flac", "0", False)
        pp = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio")
        assert pp["preferredcodec"] == "flac"

    def test_preferred_quality_passed(self):
        opts = build_ydl_opts("/tmp", "mp3", "7", False)
        pp = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio")
        assert pp["preferredquality"] == "7"

    def test_ffmpeg_metadata_added_for_best(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        keys = [pp.get("key") for pp in opts["postprocessors"]]
        assert "FFmpegMetadata" in keys

    def test_embed_thumbnail_for_mp3(self):
        opts = build_ydl_opts("/tmp", "mp3", "5", False)
        assert opts["writethumbnail"] is True
        assert opts["embedthumbnail"] is True

    def test_no_embed_thumbnail_for_wav(self):
        opts = build_ydl_opts("/tmp", "wav", "0", False)
        assert opts["writethumbnail"] is False
        assert opts["embedthumbnail"] is False

    def test_embed_thumbnail_for_flac(self):
        opts = build_ydl_opts("/tmp", "flac", "0", False)
        assert opts["writethumbnail"] is True

    def test_embed_thumbnail_for_m4a(self):
        opts = build_ydl_opts("/tmp", "m4a", "5", False)
        assert opts["writethumbnail"] is True

    def test_progress_hook_passed(self):
        hook = lambda d: None
        opts = build_ydl_opts("/tmp", "best", "0", False, progress_hook=hook)
        assert hook in opts["progress_hooks"]

    def test_no_progress_hook_by_default(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert opts["progress_hooks"] == []

    def test_custom_outtmpl_override(self):
        custom = "/custom/path/%(title)s.%(ext)s"
        opts = build_ydl_opts("/tmp", "mp3", "5", False, outtmpl=custom)
        assert opts["outtmpl"] == custom

    def test_expands_user_home(self, tmp_path):
        target = str(tmp_path / "music")
        with patch("os.path.expanduser", return_value=target):
            opts = build_ydl_opts("~/music", "best", "0", False)
        assert opts["outtmpl"].startswith(str(tmp_path))

    def test_quiet_and_no_warnings(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert opts["quiet"] is True
        assert opts["no_warnings"] is True

    def test_retries_set(self):
        opts = build_ydl_opts("/tmp", "best", "0", False)
        assert opts["retries"] == 5
        assert opts["fragment_retries"] == 5

    def test_vorbis_codec_passed_as_is(self):
        opts = build_ydl_opts("/tmp", "vorbis", "5", False)
        pp = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio")
        assert pp["preferredcodec"] == "vorbis"


class TestFetchInfo:
    """Tests for fetch_info."""

    @patch("audio_extractor.downloader.yt_dlp.YoutubeDL")
    def test_calls_extract_info(self, MockYDL):
        instance = MockYDL.return_value.__enter__.return_value
        instance.extract_info.return_value = {"title": "Test"}
        result = fetch_info("http://example.com", {})
        instance.extract_info.assert_called_once_with("http://example.com", download=False)

    @patch("audio_extractor.downloader.yt_dlp.YoutubeDL")
    def test_returns_dict(self, MockYDL):
        instance = MockYDL.return_value.__enter__.return_value
        instance.extract_info.return_value = {"title": "Test"}
        result = fetch_info("http://example.com", {})
        assert isinstance(result, dict)

    @patch("audio_extractor.downloader.yt_dlp.YoutubeDL")
    def test_returns_empty_dict_on_none(self, MockYDL):
        instance = MockYDL.return_value.__enter__.return_value
        instance.extract_info.return_value = None
        result = fetch_info("http://example.com", {})
        assert result == {}


class TestRunDownload:
    """Tests for run_download."""

    @patch("audio_extractor.downloader.yt_dlp.YoutubeDL")
    def test_calls_download(self, MockYDL):
        instance = MockYDL.return_value.__enter__.return_value
        run_download("http://example.com", {})
        instance.download.assert_called_once_with(["http://example.com"])
