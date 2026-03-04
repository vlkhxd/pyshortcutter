import time
import threading
from pynput import keyboard
from PySide6 import QtCore

from media import (
    press_vk,
    VK_MEDIA_PLAY_PAUSE,
    VK_MEDIA_NEXT_TRACK,
    VK_VOLUME_MUTE,
    VK_VOLUME_DOWN,
    VK_VOLUME_UP,
)


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _key_matches(key, bind: str) -> bool:
    """
    bind examples:
      - "f6".."f12"
      - single character like "ё", "n", "1"
    """
    b = _norm(bind)
    if not b:
        return False

    if b.startswith("f") and b[1:].isdigit():
        fn = int(b[1:])
        if 1 <= fn <= 24:
            try:
                return key == getattr(keyboard.Key, f"f{fn}")
            except AttributeError:
                return False

    # single character binding
    if isinstance(key, keyboard.KeyCode) and key.char is not None:
        return key.char == bind  # keep case/symbol exact for things like "ё"

    return False


class Controller(QtCore.QObject):
    show_osd = QtCore.Signal(str, str)      # text, accent
    state_changed = QtCore.Signal(bool)     # enabled/disabled

    GREEN = "#22c55e"
    RED = "#ef4444"

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg

        self.enabled = bool(cfg.get("enabled", True))
        self._debounce: dict[str, float] = {}
        self._debounce_sec = 0.25

        # Toggle safety: one toggle per press+release cycle
        self._toggle_down = False

    def _debounced(self, key: str) -> bool:
        now = time.time()
        last = self._debounce.get(key, 0.0)
        if now - last >= self._debounce_sec:
            self._debounce[key] = now
            return True
        return False

    def set_enabled(self, value: bool):
        if self.enabled == value:
            return
        self.enabled = value
        self.cfg["enabled"] = value

        self.state_changed.emit(value)

        if value:
            self.show_osd.emit("HOTKEYS ENABLED", self.GREEN)
        else:
            self.show_osd.emit("HOTKEYS DISABLED", self.RED)

    def toggle_enabled(self):
        self.set_enabled(not self.enabled)

    def _feature_on(self, feature_name: str) -> bool:
        feats = self.cfg.get("features", {})
        # default True if missing
        return bool(feats.get(feature_name, True))

    def media_action(self, action: str):
        if not self.enabled:
            return
        if not self._feature_on(action):
            return
        if not self._debounced(action):
            return

        if action == "playpause":
            press_vk(VK_MEDIA_PLAY_PAUSE)
        elif action == "next":
            press_vk(VK_MEDIA_NEXT_TRACK)
        elif action == "mute":
            press_vk(VK_VOLUME_MUTE)
        elif action == "voldown":
            press_vk(VK_VOLUME_DOWN)
        elif action == "volup":
            press_vk(VK_VOLUME_UP)


def start_listener(ctrl: Controller) -> threading.Thread:
    """
    Starts pynput listener in a daemon thread.
    Hotkeys are read from ctrl.cfg dynamically (so changes from Settings apply immediately).
    """
    def on_press(key):
        hk = ctrl.cfg.get("hotkeys", {})

        # Toggle (press arms, release triggers)
        if _key_matches(key, hk.get("toggle", "f6")):
            ctrl._toggle_down = True
            return

        if not ctrl.enabled:
            return

        # Actions
        if _key_matches(key, hk.get("playpause_ru", "ё")):
            ctrl.media_action("playpause")
            return

        if _key_matches(key, hk.get("next", "f8")):
            ctrl.media_action("next")
            return

        if _key_matches(key, hk.get("playpause", "f9")):
            ctrl.media_action("playpause")
            return

        if _key_matches(key, hk.get("mute", "f10")):
            ctrl.media_action("mute")
            return

        if _key_matches(key, hk.get("voldown", "f11")):
            ctrl.media_action("voldown")
            return

        if _key_matches(key, hk.get("volup", "f12")):
            ctrl.media_action("volup")
            return

    def on_release(key):
        hk = ctrl.cfg.get("hotkeys", {})
        if _key_matches(key, hk.get("toggle", "f6")) and ctrl._toggle_down:
            ctrl._toggle_down = False
            ctrl.toggle_enabled()

    def run():
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t