import json
import os

class ThemeManager:
    def __init__(self, config_path="theme_config.json"):
        self.config_path = config_path
        self._callbacks = []
        self._colors = self._load_colors()

    def _load_colors(self):
        # Default colors if config doesn't exist or is broken
        default_colors = {
            "bg": "#1e1e1e",
            "fg": "#ffffff",
            "fg_dim": "#aaaaaa",
            "accent": "#007acc",
            "surface2": "#2d2d2d",
            "accent_bg": "#007acc",
            "accent_fg": "#ffffff"
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_colors = json.load(f)
                    # Merge user colors into defaults
                    return {**default_colors, **user_colors}
            except Exception:
                return default_colors
        return default_colors

    def get_color(self, key):
        return self._colors.get(key, self._colors["fg"])

    def update_color(self, key, value):
        if key in self._colors and self._colors[key] != value:
            self._colors[key] = value
            self.save_colors()
            self._notify()

    def save_colors(self):
        try:
            # We only save the user-defined part of the colors to avoid overwriting defaults
            # In a real app, you'd track which ones are "user-set"
            with open(self.config_path, 'w') as f:
                json.dump(self._colors, f, indent=4)
        except Exception as e:
            print(f"Error saving theme: {e}")

    def register_subscriber(self, callback):
        """callback should accept (theme_dict)"""
        self._callbacks.append(callback)
        # Immediately call the callback with the current theme to initialize the subscriber
        callback(self._colors)

    def _notify(self):
        for callback in self._callbacks:
            try:
                callback(self._colors)
            except Exception as e:
                print(f"Error in theme subscriber: {e}")

    def apply_theme(self, theme_dict):
        """This mimics the old 'apply' method but uses the new structure."""
        self._colors.update(theme_dict)
        self.save_colors()
        self._notify()

# Global instance
theme = ThemeManager()
