import json

from scanpdf.models import Settings, to_dict
from scanpdf.services.paths import data_dir


class SettingsManager:
    def __init__(self):
        self.path = data_dir() / "settings.json"
        self.data = {"theme": "light", "settings": to_dict(Settings()), "output_dir": ""}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass

    def settings(self):
        defaults = to_dict(Settings())
        defaults.update(self.data.get("settings", {}))
        return Settings(**{key: value for key, value in defaults.items() if key in defaults})

    def save(self, settings, theme=None, output_dir=None):
        self.data["settings"] = to_dict(settings)
        if theme:
            self.data["theme"] = theme
        if output_dir is not None:
            self.data["output_dir"] = output_dir
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

