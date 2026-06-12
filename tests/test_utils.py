"""Tests for audio_extractor.utils."""
from unittest.mock import patch

from audio_extractor.utils import check_dependencies


class TestCheckDependencies:
    """Tests for check_dependencies."""

    def test_returns_true_when_all_present(self):
        with patch("audio_extractor.utils.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = check_dependencies(raise_on_missing=False)
        assert result is True

    def test_raises_runtime_error_when_ffmpeg_missing(self):
        with patch("audio_extractor.utils.shutil.which", return_value=None):
            try:
                check_dependencies(raise_on_missing=True)
                raise AssertionError("Should have raised RuntimeError")
            except RuntimeError as e:
                assert "ffmpeg" in str(e)

    def test_raises_runtime_error_when_ytdlp_missing(self):
        with patch("audio_extractor.utils.shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch.dict("sys.modules", {"yt_dlp": None}):
                try:
                    check_dependencies(raise_on_missing=True)
                    raise AssertionError("Should have raised RuntimeError")
                except RuntimeError as e:
                    assert "yt-dlp" in str(e)

    def test_returns_false_via_exit_when_ffmpeg_missing_and_no_raise(self):
        with patch("audio_extractor.utils.shutil.which", return_value=None):
            with patch("audio_extractor.utils.sys.exit") as mock_exit:
                check_dependencies(raise_on_missing=False)
                mock_exit.assert_called_once_with(1)
