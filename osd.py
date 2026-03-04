import ctypes
from PySide6 import QtCore, QtGui, QtWidgets

# WinAPI click-through / no-activate
user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED     = 0x00080000
WS_EX_TOOLWINDOW  = 0x00000080
WS_EX_NOACTIVATE  = 0x08000000


def _make_clickthrough_noactivate(hwnd: int) -> None:
    exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    exstyle |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)


class OSD(QtWidgets.QWidget):
    """
    Single overlay widget.
    New messages CANCEL the previous animation/timer and restart cleanly.
    """

    def __init__(self, osd_cfg: dict):
        super().__init__()
        self._cfg = osd_cfg

        self.setWindowFlags(
            QtCore.Qt.Tool
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlag(QtCore.Qt.WindowDoesNotAcceptFocus, True)

        # UI
        self.card = QtWidgets.QFrame(objectName="card")
        self.accent = QtWidgets.QFrame(objectName="accent")
        self.accent.setFixedWidth(6)

        self.dot = QtWidgets.QLabel("●", objectName="dot")
        self.dot.setFont(QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold))

        self.label = QtWidgets.QLabel("", objectName="label")
        self.label.setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Bold))

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)
        row.addWidget(self.dot, 0, QtCore.Qt.AlignVCenter)
        row.addWidget(self.label, 1, QtCore.Qt.AlignVCenter)

        inner = QtWidgets.QHBoxLayout(self.card)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        inner.addWidget(self.accent)
        inner.addLayout(row)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.card)

        self.setStyleSheet("""
            QFrame#card {
                background: #0b0f14;
                border: 1px solid #1b2430;
                border-radius: 10px;
            }
            QFrame#accent {
                background: #22c55e;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }
            QLabel#label { color: #e8edf2; }
            QLabel#dot { color: #22c55e; }
        """)

        # Opacity effect
        self.opacity = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(0.0)

        # One animation reused for both in/out
        self.anim = QtCore.QPropertyAnimation(self.opacity, b"opacity", self)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        # Single-shot hold timer
        self.hold_timer = QtCore.QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self._fade_out)

        # Connect finished ONCE
        self.anim.finished.connect(self._on_anim_finished)
        self._target_hide_on_finish = False

        self._winapi_applied = False
        self.hide()

    def _apply_winapi_flags_once(self):
        if self._winapi_applied:
            return
        hwnd = int(self.winId())
        _make_clickthrough_noactivate(hwnd)
        self._winapi_applied = True

    def _on_anim_finished(self):
        # Hide only when fade-out requested
        if self._target_hide_on_finish and self.opacity.opacity() <= 0.01:
            self._target_hide_on_finish = False
            self.hide()

    def _cfg_int(self, key: str, default: int) -> int:
        try:
            return int(self._cfg.get(key, default))
        except Exception:
            return default

    def show_message(self, text: str, accent_hex: str, hold_ms: int | None = None):
        # Read config
        hold_ms = int(hold_ms) if hold_ms is not None else self._cfg_int("hold_ms", 3500)
        fade_in_ms = self._cfg_int("fade_in_ms", 140)
        fade_out_ms = self._cfg_int("fade_out_ms", 240)
        off_x = self._cfg_int("offset_x", 34)
        off_y = self._cfg_int("offset_y", 34)

        # ---- HARD RESET previous cycle (prevents overlap) ----
        self.hold_timer.stop()
        self.anim.stop()
        self._target_hide_on_finish = False
        # ------------------------------------------------------

        # Update UI content
        self.label.setText(text)
        self.accent.setStyleSheet(
            f"background: {accent_hex}; border-top-left-radius: 10px; border-bottom-left-radius: 10px;"
        )
        self.dot.setStyleSheet(f"color: {accent_hex};")

        # Position
        self.adjustSize()
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        x = screen.x() + screen.width() - self.width() - off_x
        y = screen.y() + off_y
        self.move(x, y)

        # Show and apply WinAPI flags
        self.show()
        self.raise_()
        self._apply_winapi_flags_once()

        # Start fade-in from current opacity (but ensure visible)
        current = float(self.opacity.opacity())
        if current < 0.05:
            self.opacity.setOpacity(0.0)
            current = 0.0

        self.anim.setDuration(fade_in_ms)
        self.anim.setStartValue(current)
        self.anim.setEndValue(0.94)
        self.anim.start()

        # Store fade-out duration for later
        self._fade_out_ms = fade_out_ms

        # Hold then fade-out
        self.hold_timer.start(hold_ms)

    def _fade_out(self):
        # Cancel any running animation first
        self.anim.stop()

        self._target_hide_on_finish = True
        current = float(self.opacity.opacity())

        self.anim.setDuration(getattr(self, "_fade_out_ms", 240))
        self.anim.setStartValue(current)
        self.anim.setEndValue(0.0)
        self.anim.start()