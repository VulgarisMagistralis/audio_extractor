"""Tests for audio_extractor.theme_registry."""
import json
import os
from unittest.mock import patch, MagicMock

from audio_extractor.theme_registry import ThemeManager


class TestThemeManager:
    """Tests for ThemeManager."""

    def _make_path(self, tmp_path, name="theme_config.json"):
        return str(tmp_path / name)

    def test_default_colors_exist(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        assert "bg" in tm._colors
        assert "fg" in tm._colors

    def test_default_bg(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        assert tm._colors["bg"] == "#1e1e1e"

    def test_get_color_returns_value(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        assert tm.get_color("bg") == "#1e1e1e"

    def test_get_color_missing_key_returns_fg(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        assert tm.get_color("nonexistent") == tm._colors["fg"]

    def test_update_color_changes_value(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        tm.update_color("bg", "#00ff00")
        assert tm._colors["bg"] == "#00ff00"

    def test_update_color_same_value_no_save(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        with patch.object(tm, "save_colors") as mock_save:
            tm.update_color("bg", tm._colors["bg"])
            mock_save.assert_not_called()

    def test_update_unknown_key_no_change(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        tm.update_color("unknown_key", "#000000")
        assert "unknown_key" not in tm._colors

    def test_save_colors_writes_file(self, tmp_path):
        path = self._make_path(tmp_path)
        tm = ThemeManager(config_path=path)
        tm.save_colors()
        assert os.path.exists(path)

    def test_load_colors_from_file(self, tmp_path):
        file_path = self._make_path(tmp_path)
        custom = {"bg": "#ff0000", "fg": "#00ff00"}
        with open(file_path, "w") as f:
            json.dump(custom, f)
        tm = ThemeManager(config_path=file_path)
        assert tm._colors["bg"] == "#ff0000"

    def test_load_bad_json_uses_defaults(self, tmp_path):
        file_path = self._make_path(tmp_path)
        with open(file_path, "w") as f:
            f.write("not json at all {{{")
        tm = ThemeManager(config_path=file_path)
        assert tm._colors["bg"] == "#1e1e1e"

    def test_register_subscriber_called_immediately(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        callback = MagicMock()
        tm.register_subscriber(callback)
        callback.assert_called_once()

    def test_register_subscriber_receives_colors(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        callback = MagicMock()
        tm.register_subscriber(callback)
        call_args = callback.call_args[0][0]
        assert call_args["bg"] == "#1e1e1e"

    def test_update_notifies_subscribers(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        callback = MagicMock()
        tm.register_subscriber(callback)
        callback.reset_mock()
        tm.update_color("bg", "#00ff00")
        callback.assert_called_once()

    def test_multiple_subscribers_notified(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        cb1 = MagicMock()
        cb2 = MagicMock()
        tm.register_subscriber(cb1)
        tm.register_subscriber(cb2)
        cb1.reset_mock()
        cb2.reset_mock()
        tm.update_color("accent", "#ff0000")
        assert cb1.called
        assert cb2.called

    def test_apply_theme_updates_colors(self, tmp_path):
        tm = ThemeManager(config_path=self._make_path(tmp_path))
        tm.apply_theme({"bg": "#aabbcc"})
        assert tm._colors["bg"] == "#aabbcc"

    def test_notify_handles_subscriber_exception(self, tmp_path):
        """_notify wraps each callback in try/except so one failing callback doesn't stop others."""
        tm = ThemeManager(config_path=self._make_path(tmp_path))

        results = []

        def good_cb(_colors):
            results.append("good")

        def bad_cb(_colors):
            raise RuntimeError("boom")

        tm._callbacks.append(good_cb)
        tm._callbacks.append(bad_cb)
        tm._callbacks.append(good_cb)

        tm._notify()
        assert results == ["good", "good"]

    def test_user_colors_merge_into_defaults(self, tmp_path):
        file_path = self._make_path(tmp_path)
        partial = {"bg": "#ff0000"}
        with open(file_path, "w") as f:
            json.dump(partial, f)
        tm = ThemeManager(config_path=file_path)
        assert tm._colors["bg"] == "#ff0000"
        assert tm._colors["fg"] == "#ffffff"
