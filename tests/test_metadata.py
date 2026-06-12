"""Tests for audio_extractor.metadata."""
from audio_extractor.metadata import FORMAT_CODEC_MAP, safe_stem


class TestFormatCodecMap:
    """Tests for FORMAT_CODEC_MAP."""

    def test_has_mp3(self):
        assert FORMAT_CODEC_MAP["mp3"] == "libmp3lame"

    def test_has_flac(self):
        assert FORMAT_CODEC_MAP["flac"] == "flac"

    def test_has_wav(self):
        assert FORMAT_CODEC_MAP["wav"] == "pcm_s16le"

    def test_has_opus(self):
        assert FORMAT_CODEC_MAP["opus"] == "libopus"

    def test_best_is_none(self):
        assert FORMAT_CODEC_MAP["best"] is None

    def test_m4a_maps_to_aac_codec(self):
        assert FORMAT_CODEC_MAP["m4a"] == "aac"

    def test_vorbis_maps_to_libvorbis(self):
        assert FORMAT_CODEC_MAP["vorbis"] == "libvorbis"

    def test_has_eight_entries(self):
        assert len(FORMAT_CODEC_MAP) == 8


class TestSafeStem:
    """Tests for safe_stem."""

    def test_simple_name_unchanged(self):
        assert safe_stem("My Song") == "My Song"

    def test_removes_backslash(self):
        assert safe_stem("a\\b") == "a_b"

    def test_removes_forward_slash(self):
        assert safe_stem("a/b") == "a_b"

    def test_removes_colon(self):
        assert safe_stem("Hello:World") == "Hello_World"

    def test_removes_asterisk(self):
        assert safe_stem("a*b") == "a_b"

    def test_removes_question_mark(self):
        assert safe_stem("what?") == "what_"

    def test_removes_double_quote(self):
            assert safe_stem('say "hi"') == 'say _hi_'

    def test_removes_angle_brackets(self):
        assert safe_stem("<brave>") == "_brave_"

    def test_removes_pipe(self):
        assert safe_stem("left|right") == "left_right"

    def test_strips_leading_trailing_whitespace(self):
        assert safe_stem("  hello  ") == "hello"

    def test_rstrips_trailing_dot(self):
        assert safe_stem("file.") == "file"

    def test_multiple_trailing_dots(self):
        result = safe_stem("file...")
        assert not result.endswith(".")

    def test_truncates_long_names(self):
        long = "a" * 300
        assert len(safe_stem(long)) <= 180

    def test_removes_all_invalid_chars_combined(self):
        result = safe_stem("a\\b/c:d*e?f\"g<h>i|j")
        assert '"' not in result
        assert "\\" not in result
