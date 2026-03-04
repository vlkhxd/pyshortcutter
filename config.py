import json
from pathlib import Path
from copy import deepcopy
import os

# путь к AppData/Roaming
APPDATA_DIR = Path(os.getenv("APPDATA")) / "Shortcutter"

# путь к config.json
CONFIG_PATH = APPDATA_DIR / "config.json"


DEFAULT_CONFIG = {
    "enabled": True,

    "osd": {
        "hold_ms": 3500,
        "fade_in_ms": 140,
        "fade_out_ms": 240,
        "offset_x": 34,
        "offset_y": 34
    },

    "hotkeys": {
        "toggle": "f6",
        "playpause_ru": "ё",
        "next": "f8",
        "playpause": "f9",
        "mute": "f10",
        "voldown": "f11",
        "volup": "f12"
    }
}


def _merge_defaults(user_cfg, default_cfg):
    result = deepcopy(default_cfg)

    for key, value in user_cfg.items():
        if isinstance(value, dict) and key in result:
            result[key] = _merge_defaults(value, result[key])
        else:
            result[key] = value

    return result


def load_config():
    """
    Загружает config.json.
    Если файла нет — создаёт его.
    """

    # создаём папку если её нет
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except Exception:
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    merged = _merge_defaults(user_cfg, DEFAULT_CONFIG)

    if merged != user_cfg:
        save_config(merged)

    return merged


def save_config(cfg: dict):
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)