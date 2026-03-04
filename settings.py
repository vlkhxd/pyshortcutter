from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets


def _pretty_key(s: str) -> str:
    s = (s or "").strip()
    return s.upper() if s.lower().startswith("f") else s


class KeyCaptureDialog(QtWidgets.QDialog):
    """
    Dialog that captures a single key press while it has focus.
    Returns a binding string like "f6" or "ё" or "n".
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press a key")
        self.setModal(True)
        self.setFixedWidth(360)
        self._captured: str | None = None

        lbl = QtWidgets.QLabel("Press any key now…\n(ESC to cancel)")
        lbl.setAlignment(QtCore.Qt.AlignCenter)

        self.preview = QtWidgets.QLabel("")
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setStyleSheet("font-size: 18px; font-weight: 700;")

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(lbl)
        lay.addWidget(self.preview)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()
            return

        key = event.key()

        # Function keys
        if QtCore.Qt.Key_F1 <= key <= QtCore.Qt.Key_F24:
            n = key - QtCore.Qt.Key_F1 + 1
            self._captured = f"f{n}"
            self.preview.setText(_pretty_key(self._captured))
            self.accept()
            return

        text = event.text()
        if text:
            # For symbols/letters like "ё", "n"
            self._captured = text
            self.preview.setText(_pretty_key(self._captured))
            self.accept()
            return

        # If no text (rare), ignore
        event.ignore()

    @property
    def captured(self) -> str | None:
        return self._captured


class SettingsDialog(QtWidgets.QDialog):
    """
    Tabs:
      - General: enabled + OSD settings
      - Hotkeys & Features: enable/disable actions + change key bindings
    Writes changes into cfg dict (in-place) on Save.
    """
    def __init__(self, parent: QtWidgets.QWidget | None, cfg: dict):
        super().__init__(parent)
        self.cfg = cfg

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.tabs = QtWidgets.QTabWidget()

        self._build_general_tab()
        self._build_hotkeys_tab()

        # Buttons
        self.btn_save = QtWidgets.QPushButton("Save")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_save.setDefault(True)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(btns)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

    # -------- General tab --------
    def _build_general_tab(self):
        tab = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(tab)

        self.enabled_cb = QtWidgets.QCheckBox("Hotkeys enabled")
        self.enabled_cb.setChecked(bool(self.cfg.get("enabled", True)))
        form.addRow(self.enabled_cb)

        osd = self.cfg.get("osd", {})

        self.hold_ms = QtWidgets.QSpinBox()
        self.hold_ms.setRange(300, 20000)
        self.hold_ms.setSingleStep(100)
        self.hold_ms.setValue(int(osd.get("hold_ms", 3500)))

        self.fade_in_ms = QtWidgets.QSpinBox()
        self.fade_in_ms.setRange(0, 5000)
        self.fade_in_ms.setSingleStep(10)
        self.fade_in_ms.setValue(int(osd.get("fade_in_ms", 140)))

        self.fade_out_ms = QtWidgets.QSpinBox()
        self.fade_out_ms.setRange(0, 5000)
        self.fade_out_ms.setSingleStep(10)
        self.fade_out_ms.setValue(int(osd.get("fade_out_ms", 240)))

        self.offset_x = QtWidgets.QSpinBox()
        self.offset_x.setRange(0, 2000)
        self.offset_x.setValue(int(osd.get("offset_x", 34)))

        self.offset_y = QtWidgets.QSpinBox()
        self.offset_y.setRange(0, 2000)
        self.offset_y.setValue(int(osd.get("offset_y", 34)))

        form.addRow("OSD hold (ms):", self.hold_ms)
        form.addRow("Fade in (ms):", self.fade_in_ms)
        form.addRow("Fade out (ms):", self.fade_out_ms)
        form.addRow("Offset X (px):", self.offset_x)
        form.addRow("Offset Y (px):", self.offset_y)

        form.addRow(QtWidgets.QLabel(""))

        hint = QtWidgets.QLabel("Tip: Hotkeys & features are on the next tab.")
        hint.setStyleSheet("color: #8b98a5;")
        form.addRow(hint)

        self.tabs.addTab(tab, "General")

    # -------- Hotkeys tab --------
    def _build_hotkeys_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        hk = self.cfg.get("hotkeys", {})
        feats = self.cfg.get("features", {})

        self._rows = []  # list of dicts per action

        def add_row(action_key: str, label: str, default_bind: str):
            row_w = QtWidgets.QWidget()
            row_l = QtWidgets.QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)

            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(bool(feats.get(action_key, True)))

            edit = QtWidgets.QLineEdit(_pretty_key(hk.get(action_key, default_bind) if action_key != "playpause_ru" else hk.get("playpause_ru", default_bind)))
            edit.setReadOnly(True)

            btn = QtWidgets.QPushButton("Change…")
            btn.setFixedWidth(100)

            row_l.addWidget(cb, 1)
            row_l.addWidget(edit, 0)
            row_l.addWidget(btn, 0)

            self._rows.append({
                "action": action_key,
                "checkbox": cb,
                "edit": edit,
                "default": default_bind,
                "is_ru": (action_key == "playpause_ru"),
            })

            def on_change():
                dlg = KeyCaptureDialog(self)
                if dlg.exec() == QtWidgets.QDialog.Accepted and dlg.captured:
                    edit.setText(_pretty_key(dlg.captured))

            btn.clicked.connect(on_change)
            layout.addWidget(row_w)

        # Actions
        add_row("toggle", "Toggle hotkeys", "f6")
        add_row("playpause_ru", "Play/Pause (RU key)", "ё")
        add_row("next", "Next", "f8")
        add_row("playpause", "Play/Pause", "f9")
        add_row("mute", "Mute", "f10")
        add_row("voldown", "Volume down", "f11")
        add_row("volup", "Volume up", "f12")

        layout.addStretch(1)

        note = QtWidgets.QLabel("Note: Changes apply immediately (no restart).")
        note.setStyleSheet("color: #8b98a5;")
        layout.addWidget(note)

        self.tabs.addTab(tab, "Hotkeys & Features")

    def _on_save(self):
        # enabled
        self.cfg["enabled"] = bool(self.enabled_cb.isChecked())

        # osd
        osd = self.cfg.setdefault("osd", {})
        osd["hold_ms"] = int(self.hold_ms.value())
        osd["fade_in_ms"] = int(self.fade_in_ms.value())
        osd["fade_out_ms"] = int(self.fade_out_ms.value())
        osd["offset_x"] = int(self.offset_x.value())
        osd["offset_y"] = int(self.offset_y.value())

        # hotkeys + features
        hk = self.cfg.setdefault("hotkeys", {})
        feats = self.cfg.setdefault("features", {})

        for row in self._rows:
            action = row["action"]
            enabled = bool(row["checkbox"].isChecked())
            feats[action if action != "playpause_ru" else "playpause"] = enabled if action == "playpause_ru" else enabled
            # store binding
            bind = row["edit"].text().strip()
            bind = bind.lower() if bind.lower().startswith("f") else bind  # keep symbols like "ё"
            if action == "playpause_ru":
                hk["playpause_ru"] = bind
            else:
                hk[action] = bind

        self.accept()