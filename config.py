import json
import os
from copy import deepcopy
from pathlib import Path

# путь к AppData/Roaming
APPDATA_DIR = Path(os.getenv("APPDATA") or "") / "Shortcutter"

# путь к config.json
CONFIG_PATH = APPDATA_DIR / "config.json"

# Текущая версия схемы конфига
CONFIG_VERSION = 1

DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,

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
        "prev": "f7",
        "next": "f8",
        "playpause": "f9",
        "mute": "f10",
        "voldown": "f11",
        "volup": "f12"
    },

    "features": {
        "playpause": True,
        "prev": True,
        "next": True,
        "mute": True,
        "voldown": True,
        "volup": True
    }
}


def _merge_defaults(user_cfg: dict, default_cfg: dict) -> dict:
    """
    Deep-merge: добавляет недостающие поля из default_cfg,
    сохраняя пользовательские значения.
    """
    result = deepcopy(default_cfg)

    for key, value in user_cfg.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_defaults(value, result[key])
        else:
            result[key] = value

    return result


def _migrate_config(cfg: dict, from_version: int) -> dict:
    """
    Миграции схемы конфига.
    from_version — версия, которая была в файле (или 0 если не было).
    """
    # v0 -> v1: добавили prev, features, config_version
    if from_version < 1:
        cfg.setdefault("hotkeys", {}).setdefault("prev", "f7")
        feats = cfg.setdefault("features", {})
        feats.setdefault("playpause", True)
        feats.setdefault("prev", True)
        feats.setdefault("next", True)
        feats.setdefault("mute", True)
        feats.setdefault("voldown", True)
        feats.setdefault("volup", True)

    cfg["config_version"] = CONFIG_VERSION
    return cfg


def load_config() -> dict:
    """
    Загружает config.json.
    Если файла нет — создаёт его.
    Если конфиг старой версии — мигрирует и сохраняет.
    """
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        cfg = deepcopy(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except Exception:
        cfg = deepcopy(DEFAULT_CONFIG)
        save_config(cfg)
        return cfg

    # Версия из файла (если не было — считаем 0)
    file_version = int(user_cfg.get("config_version", 0) or 0)

    # Мержим дефолты, чтобы новые поля всегда появлялись
    merged = _merge_defaults(user_cfg, DEFAULT_CONFIG)

    # Мигрируем, если нужно
    if file_version < CONFIG_VERSION:
        merged = _migrate_config(merged, file_version)

    # Если что-то изменилось — сохраняем обратно
    if merged != user_cfg:
        save_config(merged)

    return merged


def save_config(cfg: dict) -> None:
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)

    # Всегда ставим актуальную версию схемы при сохранении
    cfg = deepcopy(cfg)
    cfg["config_version"] = CONFIG_VERSION

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)