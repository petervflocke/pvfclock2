from copy import deepcopy
from pathlib import Path
import os
import subprocess
import sys
from threading import Event

import pytest
from PyQt5.QtCore import QThread, QTimer

from app_config import AppConfig, DEFAULT_CONFIG
from metrics_provider import MetricValue
from monitor_controller import MonitorController


class BlockingProvider:
    def __init__(self):
        self.entered = Event()
        self.release = Event()
        self.calls = 0
        self.refreshes = 0
        self.fail = False
        self.configs = []
        self.threads = []

    def collect(self):
        self.calls += 1
        self.configs.append(deepcopy(self.config))
        self.threads.append(QThread.currentThread())
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("Test did not release provider")
        if self.fail:
            self.fail = False
            raise RuntimeError("collection failure")
        return [MetricValue("cpu", "CPU", 25.0, "25%", "%", True)]

    def force_external_ip_refresh(self):
        self.refreshes += 1


class Panel:
    def __init__(self):
        self.visible = True
        self.updates = []
        self.threads = []
        self.fail = False

    def isVisible(self):
        return self.visible

    def set_metrics(self, metrics, history):
        self.threads.append(QThread.currentThread())
        if self.fail:
            self.fail = False
            raise RuntimeError("display failure")
        self.updates.append((metrics, history))


@pytest.fixture
def monitor(qtbot, tmp_path):
    config = AppConfig(tmp_path / "test.yaml", deepcopy(DEFAULT_CONFIG))
    panel = Panel()
    provider = BlockingProvider()
    controller = MonitorController(config, panel, provider)
    yield controller, provider, panel, config
    provider.release.set()
    controller.stop()
    qtbot.waitUntil(lambda: not controller.thread.isRunning())


def test_slow_collection_keeps_gui_responsive_and_uses_correct_threads(monitor, qtbot, qapp):
    controller, provider, panel, _ = monitor
    beats = []
    heartbeat = QTimer()
    heartbeat.setInterval(5)
    heartbeat.timeout.connect(lambda: beats.append(True))
    heartbeat.start()
    controller.poll()
    qtbot.waitUntil(provider.entered.is_set)
    qtbot.waitUntil(lambda: len(beats) >= 3)
    assert not panel.updates
    provider.release.set()
    qtbot.waitUntil(lambda: len(panel.updates) == 1)
    heartbeat.stop()
    assert provider.threads == [controller.thread]
    assert panel.threads == [qapp.thread()]


def test_timer_ticks_skip_busy_worker_and_explicit_refreshes_coalesce(monitor, qtbot):
    controller, provider, panel, _ = monitor
    controller.poll()
    qtbot.waitUntil(provider.entered.is_set)
    for _ in range(10):
        controller._timer_poll()
    assert not controller._pending_poll
    for _ in range(10):
        controller.poll()
    assert provider.calls == 1
    provider.release.set()
    qtbot.waitUntil(lambda: len(panel.updates) == 2)
    assert provider.calls == 2
    assert not controller._busy


def test_failed_collection_logs_and_next_poll_succeeds(monitor, qtbot, caplog):
    controller, provider, panel, _ = monitor
    provider.release.set()
    controller.poll()
    qtbot.waitUntil(lambda: len(panel.updates) == 1)
    history = controller.history["cpu"].as_list()
    provider.fail = True
    controller.poll()
    qtbot.waitUntil(lambda: not controller._busy)
    assert len(panel.updates) == 1
    assert controller.history["cpu"].as_list() == history
    assert "collection failure" in caplog.text
    controller.poll()
    qtbot.waitUntil(lambda: len(panel.updates) == 2)


def test_display_failure_does_not_wedge_polling(monitor, qtbot, caplog):
    controller, provider, panel, _ = monitor
    provider.release.set()
    panel.fail = True
    controller.poll()
    qtbot.waitUntil(lambda: not controller._busy)
    assert "display failure" in caplog.text
    controller.poll()
    qtbot.waitUntil(lambda: len(panel.updates) == 1)


def test_reload_discards_stale_result_and_keeps_refresh_intent(monitor, qtbot):
    controller, provider, panel, config = monitor
    controller.poll()
    qtbot.waitUntil(provider.entered.is_set)
    config.data["metrics"]["cpu"]["label"] = "New CPU"
    config.data["app"]["collect_history"]["history_minutes"] = 1
    controller.configure(config)
    controller.refresh_external_ip()
    controller.refresh_external_ip()
    provider.release.set()
    qtbot.waitUntil(lambda: provider.calls == 2 and not controller._busy)
    assert len(panel.updates) == 1
    assert controller.history["cpu"].as_list() == [25.0]
    assert controller.history["cpu"].capacity == 12
    assert provider.configs[0]["metrics"]["cpu"]["label"] == "CPU"
    assert provider.configs[1]["metrics"]["cpu"]["label"] == "New CPU"
    assert provider.refreshes == 1


def test_panel_visible_mode_skips_hidden_collection_and_late_result(monitor, qtbot):
    controller, provider, panel, config = monitor
    config.data["app"]["collect_history"]["mode"] = "panel_visible"
    controller.configure(config)
    panel.visible = False
    controller.refresh_external_ip()
    assert not controller._busy
    panel.visible = True
    controller.poll()
    qtbot.waitUntil(provider.entered.is_set)
    panel.visible = False
    provider.release.set()
    qtbot.waitUntil(lambda: not controller._busy)
    assert not panel.updates
    assert not controller.history
    assert provider.refreshes == 1


def test_always_mode_collects_while_hidden(monitor, qtbot):
    controller, provider, panel, _ = monitor
    panel.visible = False
    provider.release.set()
    controller.poll()
    qtbot.waitUntil(lambda: len(panel.updates) == 1)


def test_shutdown_during_collection_ignores_result_and_pending_requests(monitor, qtbot):
    controller, provider, panel, _ = monitor
    controller.start()
    qtbot.waitUntil(provider.entered.is_set)
    controller.refresh_external_ip()
    controller.stop()
    controller.stop()
    assert not controller.timer.isActive()
    assert controller.thread.isRunning()
    controller.poll()
    with qtbot.waitSignal(controller.shutdown_finished):
        provider.release.set()
    assert not controller.thread.isRunning()
    assert provider.calls == 1
    assert not panel.updates
    assert not controller.history


@pytest.mark.parametrize("quit_method", ["close", "shortcut"])
def test_window_shutdown_waits_for_active_worker(tmp_path, quit_method):
    # Use a subprocess because QApplication.quit() would end pytest-qt's event loop.
    script = r'''
import sys
from copy import deepcopy
from pathlib import Path
from threading import Event
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
from app_config import AppConfig, DEFAULT_CONFIG
from metrics_provider import SystemMetricsProvider
import digitalclock

entered = Event()
release = Event()
def collect(self):
    entered.set()
    if not release.wait(5):
        raise RuntimeError("shutdown blocked the GUI")
    return []
SystemMetricsProvider.collect = collect
app = QApplication([])
config = AppConfig(Path(sys.argv[1]), deepcopy(DEFAULT_CONFIG))
digitalclock.params = config.clock_params()
window = digitalclock.MainWindow(config)
window.activateWindow()
requested = []
def request_shutdown():
    if not entered.is_set():
        QTimer.singleShot(10, request_shutdown)
        return
    if sys.argv[2] == "shortcut":
        QTest.keyClick(window, Qt.Key_Q, Qt.ControlModifier)
    else:
        window.close()
    requested.append(window._shutdown_started)
    # This callback must execute while shutdown is awaiting the worker.
    QTimer.singleShot(30, release.set)
QTimer.singleShot(30, request_shutdown)
app.exec_()
assert requested == [True]
assert window._shutdown_complete
assert not window.monitor_controller.thread.isRunning()
print("clean shutdown")
'''
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "config.yaml"), quit_method],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "clean shutdown" in result.stdout
    assert "QThread: Destroyed" not in result.stderr
