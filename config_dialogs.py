from __future__ import annotations

from pathlib import Path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QWidget

from app_config import AppConfig, ConfigLoadError


def load_startup_config(path: Path | None = None) -> AppConfig | None:
    """Return None when the user exits; fallback never writes to disk."""
    try:
        return AppConfig.load(path)
    except ConfigLoadError as error:
        print(error, file=sys.stderr)
        dialog = QMessageBox()
        dialog.setWindowTitle("Configuration error")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText(str(error))
        dialog.setInformativeText(
            "Fix the configuration, or run with temporary defaults.\n"
            "Your configuration file will remain unchanged."
        )
        exit_button = dialog.addButton("Exit", QMessageBox.RejectRole)
        defaults_button = dialog.addButton("Run with defaults", QMessageBox.AcceptRole)
        dialog.setDefaultButton(exit_button)
        dialog.setEscapeButton(exit_button)
        dialog.exec_()
        if dialog.clickedButton() is defaults_button:
            return AppConfig.temporary_defaults(error.path)
        return None


def show_reload_error(parent: QWidget, error: Exception) -> None:
    print(f"Config reload failed: {error}", file=sys.stderr)
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Config reload failed")
    dialog.setIcon(QMessageBox.Warning)
    dialog.setTextFormat(Qt.PlainText)
    dialog.setText(str(error))
    dialog.setInformativeText("The current configuration remains active.")
    dialog.exec_()
