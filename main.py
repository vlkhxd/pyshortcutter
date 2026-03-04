import sys
from PySide6 import QtCore, QtGui, QtWidgets

from config import load_config, save_config
from osd import OSD
from hotkeys import Controller, start_listener
from settings import SettingsDialog


def build_hotkeys_help_menu(parent_menu: QtWidgets.QMenu, cfg: dict):
    parent_menu.clear()
    hk = cfg.get("hotkeys", {})

    lines = [
        (hk.get("toggle", "f6"), "Toggle hotkeys"),
        (hk.get("playpause_ru", "ё"), "Play/Pause (RU key)"),
        (hk.get("prev", "f7"), "Previous / Rewind (media)"),
        (hk.get("next", "f8"), "Next"),
        (hk.get("playpause", "f9"), "Play/Pause"),
        (hk.get("mute", "f10"), "Mute"),
        (hk.get("voldown", "f11"), "Volume down"),
        (hk.get("volup", "f12"), "Volume up"),
    ]

    for key, action in lines:
        act = QtGui.QAction(f"{str(key).upper()} — {action}", parent_menu)
        act.setEnabled(False)
        parent_menu.addAction(act)


def make_icon(color: str) -> QtGui.QIcon:
    pix = QtGui.QPixmap(64, 64)
    pix.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pix)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setBrush(QtGui.QBrush(QtGui.QColor(color)))
    painter.setPen(QtCore.Qt.NoPen)
    painter.drawEllipse(10, 10, 44, 44)
    painter.end()

    return QtGui.QIcon(pix)


def create_tray(app: QtWidgets.QApplication, cfg: dict, ctrl: Controller, osd: OSD):
    tray = QtWidgets.QSystemTrayIcon(app)

    icon_enabled = make_icon("#22c55e")
    icon_disabled = make_icon("#ef4444")

    tray.setIcon(icon_enabled if bool(cfg.get("enabled", True)) else icon_disabled)
    tray.setToolTip("Shortcutter")

    menu = QtWidgets.QMenu()

    enabled_action = QtGui.QAction("Enabled", menu)
    enabled_action.setCheckable(True)
    enabled_action.setChecked(bool(cfg.get("enabled", True)))
    menu.addAction(enabled_action)

    menu.addSeparator()

    hk_menu = QtWidgets.QMenu("Hotkeys", menu)
    build_hotkeys_help_menu(hk_menu, cfg)
    menu.addMenu(hk_menu)

    settings_action = QtGui.QAction("Settings…", menu)
    settings_action.setEnabled(True)
    menu.addAction(settings_action)

    menu.addSeparator()

    exit_action = QtGui.QAction("Exit", menu)
    menu.addAction(exit_action)

    tray.setContextMenu(menu)
    tray.show()

    # --- Wiring ---

    def set_enabled_from_tray(checked: bool):
        # request state change; persistence happens in on_state_changed
        ctrl.set_enabled(checked)

    enabled_action.toggled.connect(set_enabled_from_tray)

    def on_state_changed(enabled: bool):
        enabled_action.blockSignals(True)
        enabled_action.setChecked(enabled)
        enabled_action.blockSignals(False)

        cfg["enabled"] = enabled
        save_config(cfg)

        tray.setToolTip(f"Shortcutter — {'Enabled' if enabled else 'Disabled'}")
        tray.setIcon(icon_enabled if enabled else icon_disabled)

    ctrl.state_changed.connect(on_state_changed)

    def open_settings():
        dlg = SettingsDialog(None, cfg)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            # save cfg
            save_config(cfg)

            # apply enabled state (sync tray via state_changed)
            ctrl.set_enabled(bool(cfg.get("enabled", True)))

            # rebuild hotkeys hint menu (because binds may have changed)
            build_hotkeys_help_menu(hk_menu, cfg)

            osd.show_message("SETTINGS SAVED", "#7aa2f7", hold_ms=1600)

    settings_action.triggered.connect(open_settings)

    def on_exit():
        tray.hide()
        app.quit()

    exit_action.triggered.connect(on_exit)

    # Optional: double click toggles
    def on_activated(reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            ctrl.toggle_enabled()

    tray.activated.connect(on_activated)

    return tray


def main():
    cfg = load_config()

    app = QtWidgets.QApplication(sys.argv)

    osd = OSD(cfg.get("osd", {}))
    ctrl = Controller(cfg)

    ctrl.show_osd.connect(lambda text, accent: osd.show_message(text, accent))

    start_listener(ctrl)
    create_tray(app, cfg, ctrl, osd)

    # initial state
    QtCore.QTimer.singleShot(0, lambda: ctrl.set_enabled(bool(cfg.get("enabled", True))))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()