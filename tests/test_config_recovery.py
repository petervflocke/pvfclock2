from copy import deepcopy

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from app_config import AppConfig, ConfigLoadError, DEFAULT_CONFIG
from config_dialogs import load_startup_config
import digitalclock


def test_parse_error_has_location_and_source_without_modifying_file(tmp_path):
    path = tmp_path / "broken.yaml"
    source = "clock:\n  geometry: ]\n"
    path.write_text(source)
    with pytest.raises(ConfigLoadError) as caught:
        AppConfig.load(path)
    error = caught.value
    assert (error.line, error.column) == (2, 13)
    assert str(path) in str(error)
    assert "  geometry: ]" in str(error)
    assert path.read_text() == source


@pytest.mark.parametrize("source", ["[]", "false", "0", "hello", "null"])
def test_non_mapping_is_rejected_without_overwriting(tmp_path, source):
    path = tmp_path / "config.yaml"
    path.write_text(source)
    with pytest.raises(ConfigLoadError, match="Expected a YAML mapping"):
        AppConfig.load(path)
    assert path.read_text() == source


def test_temporary_defaults_block_all_saving(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("broken: [")
    config = AppConfig.temporary_defaults(path)
    original = deepcopy(config.data)
    with pytest.raises(PermissionError, match="temporary defaults"):
        config.save()
    params = config.clock_params()
    params["x"] = 99
    with pytest.raises(PermissionError):
        config.update_clock_params(params)
    assert config.data == original == DEFAULT_CONFIG
    assert path.read_text() == "broken: ["
    config.data["clock"]["geometry"]["x"] = 10
    assert DEFAULT_CONFIG == original


@pytest.mark.parametrize("choice", ["Exit", "Run with defaults"])
def test_startup_dialog_choices(qtbot, tmp_path, capsys, choice):
    path = tmp_path / "config.yaml"
    path.write_text("broken: [")
    observed = []

    def choose():
        dialog = QApplication.activeModalWidget()
        observed.append(dialog.text())
        next(button for button in dialog.buttons() if button.text() == choice).click()

    QTimer.singleShot(0, choose)
    config = load_startup_config(path)
    assert "Line 1, column" in observed[0]
    assert str(path) in capsys.readouterr().err
    if choice == "Exit":
        assert config is None
    else:
        assert config.temporary
        assert config.data == DEFAULT_CONFIG
    assert path.read_text() == "broken: ["


def test_reload_preserves_fallback_on_error_and_restores_saving(qtbot, tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("broken: [")
    config = AppConfig.temporary_defaults(path)
    # Avoid real sensor commands during this GUI test.
    config.data["metrics"]["temperatures"]["enabled"] = False
    monkeypatch.setattr(digitalclock, "params", config.clock_params())
    errors = []
    monkeypatch.setattr(digitalclock, "show_reload_error", lambda parent, error: errors.append(error))
    window = digitalclock.MainWindow(config)
    # Test cleanup must not quit pytest's shared QApplication.
    window.monitor_controller.shutdown_finished.disconnect(window.finish_shutdown)
    try:
        window.mouseDoubleClickEvent(None)
        assert "Saving disabled" in window.statusBar().currentMessage()
        assert path.read_text() == "broken: ["
        window.reload_config()
        assert isinstance(errors[0], ConfigLoadError)
        assert window.app_config is config
        path.write_text("metrics:\n  temperatures:\n    enabled: false\n")
        window.reload_config()
        assert not window.app_config.temporary
        window.move(123, 45)
        window.mouseDoubleClickEvent(None)
        assert AppConfig.load(path).get("clock.geometry.x") == 123
    finally:
        window.monitor_controller.stop()
        qtbot.waitUntil(lambda: not window.monitor_controller.thread.isRunning())
        window._shutdown_complete = True
        window.monitor_panel.close()
        window.close()
