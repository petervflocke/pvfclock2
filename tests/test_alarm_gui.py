from dataclasses import asdict
from datetime import datetime, timedelta

import pytest
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtTest import QTest

from alarm_model import Alarm, UTC
from alarm_store import AlarmStore
from app_config import AppConfig
from alarm_controller import AlarmController
from alarm_panel import AlarmPanel
from alarm_notification import AlarmNotification
import digitalclock


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    config = AppConfig.load(tmp_path / 'config.yaml')
    config.data['metrics']['temperatures']['enabled'] = False
    config.data['alarm']['sound']['enabled'] = False
    config.save()
    monkeypatch.setattr(digitalclock, 'params', config.clock_params())
    win = digitalclock.MainWindow(config)
    win.monitor_controller.shutdown_finished.disconnect(win.finish_shutdown)
    win.alarm_controller.shutdown_finished.disconnect(win.finish_shutdown)
    yield win
    if win.notification:
        win.notification.close()
    win.alarm_controller.stop()
    win.monitor_controller.stop()
    qtbot.waitUntil(lambda: not win.alarm_controller.thread.isRunning() and not win.monitor_controller.thread.isRunning())
    win._shutdown_complete = True
    win.alarm_panel.close()
    win.monitor_panel.close()
    if hasattr(win, 'calendar_app'):
        win.calendar_app.close()
    win.close()


def test_stack_and_calendar_all_combinations(window, qtbot):
    window.show_calendar()
    for alarm_visible, monitor_visible in [(False, False), (False, True), (True, True), (True, False), (False, False)]:
        if window.alarm_panel.isVisible() != alarm_visible:
            window.toggle_alarm()
        if window.monitor_panel.isVisible() != monitor_visible:
            window.toggle_monitor()
        window.move(50, 60)
        window.resize(350, 150)
        qtbot.wait(10)
        bottom = window.y() + window.height()
        if alarm_visible:
            assert window.alarm_panel.y() == bottom
            assert window.alarm_panel.x() == window.x()
            assert window.alarm_panel.width() == window.width()
            bottom += window.alarm_panel.height()
        if monitor_visible:
            assert window.monitor_panel.y() == bottom
            bottom += window.monitor_panel.height()
        assert window.calendar_app.y() == bottom + 40


def test_monitor_fixed_width_and_height_change(window, qtbot):
    window.app_config.data['monitor_panel']['width_mode'] = 'fixed'
    window.app_config.data['monitor_panel']['fixed_width'] = 420
    window.toggle_monitor()
    window.toggle_alarm()
    window.show_calendar()
    window.app_config.data['monitor_panel']['height'] = 400
    window.monitor_panel.resize(420, 400)
    qtbot.waitUntil(lambda: window.calendar_app.y() == window.monitor_panel.y() + 400 + 40)
    assert window.monitor_panel.width() == 420
    assert window.monitor_panel.y() == window.alarm_panel.y() + window.alarm_panel.height()


def test_keyboard_arm_hide_cancel_and_replace(window, qtbot):
    qtbot.waitUntil(lambda: not window.alarm_controller.busy)
    window.activateWindow()
    QTest.keyClick(window, Qt.Key_2, Qt.ControlModifier)
    qtbot.waitUntil(window.alarm_panel.isVisible)
    panel = window.alarm_panel
    tomorrow = QDate.currentDate().addDays(1)
    panel.date.setDate(tomorrow)
    panel.time.setText('1430')
    panel.label.setText('Tea')
    QTest.keyClick(panel.time, Qt.Key_Return)
    qtbot.waitUntil(lambda: window.alarm_controller.current is not None)
    old = window.alarm_controller.current
    assert old.state == 'armed' and old.label == 'Tea'
    panel.time.setText('1530')
    QTest.keyClick(panel.time, Qt.Key_Escape)
    assert not panel.isVisible()
    assert window.alarm_controller.current == old
    window.toggle_alarm()
    assert panel.time.text() == '14:30'
    panel.time.setText('1530')
    panel.confirm()
    qtbot.waitUntil(lambda: window.alarm_controller.current.id != old.id)
    panel.cancel_button.click()
    qtbot.waitUntil(lambda: window.alarm_controller.current.state == 'cancelled')


def test_temporary_defaults_disable_arm(qtbot, tmp_path):
    config = AppConfig.temporary_defaults(tmp_path / 'config.yaml')
    panel = AlarmPanel(config)
    qtbot.addWidget(panel)
    assert not panel.set_button.isEnabled()
    assert not config.path.exists()


def test_notification_dismissal_and_bounded_sound(qtbot):
    now = datetime.now(UTC)
    alarm = Alarm.create(now + timedelta(minutes=1), 'UTC', 'Tea', now)
    dialog = AlarmNotification(alarm, {'sound': {'enabled': False, 'duration_seconds': 999}})
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.stop_timer.interval() == 30000
    dialog.activateWindow()
    QTest.keyClick(dialog, Qt.Key_Escape)
    assert not dialog.isVisible()
    assert not dialog.flash_timer.isActive()
    assert not dialog.stop_timer.isActive()


def test_controller_fires_after_persistence_and_shutdown(qtbot, tmp_path):
    config = AppConfig.load(tmp_path / 'config.yaml')
    controller = AlarmController(config)
    rings = []
    controller.ringing.connect(lambda alarm, settings: rings.append(alarm))
    try:
        qtbot.waitUntil(lambda: not controller.startup)
        now = datetime.now(UTC)
        alarm = Alarm.create(now + timedelta(seconds=1), 'UTC', 'Tea', now)
        controller.arm(alarm)
        qtbot.waitUntil(lambda: bool(rings), timeout=4000)
        controller.timer.stop()
        qtbot.waitUntil(lambda: not controller.busy)
        assert AppConfig.load(config.path).get('alarm.current')['state'] == 'fired'
        controller.poll()
        qtbot.waitUntil(lambda: not controller.busy)
        assert len(rings) == 1
    finally:
        controller.stop()
        qtbot.waitUntil(lambda: not controller.thread.isRunning())


def test_tomorrow_preview_and_segment_steps(qtbot, tmp_path):
    panel = AlarmPanel(AppConfig.temporary_defaults(tmp_path / 'config.yaml'))
    qtbot.addWidget(panel)
    panel.time.setText('0000')
    assert panel.candidates()[0].astimezone(panel.zone).date() == (datetime.now(panel.zone) + timedelta(days=1)).date()
    panel.time.setText('14:30')
    panel.time.setCursorPosition(0)
    QTest.keyClick(panel.time, Qt.Key_Up)
    assert panel.time.text() == '15:30'
    QTest.keyClick(panel.time, Qt.Key_Right)
    QTest.keyClick(panel.time, Qt.Key_Down)
    assert panel.time.text() == '15:29'
    panel.date.setDate(QDate.currentDate().addDays(-1))
    with pytest.raises(ValueError, match='future'):
        panel.candidates()


def test_audio_unavailable_still_shows_notification(qtbot, monkeypatch):
    monkeypatch.setattr('alarm_notification.QSoundEffect', None)
    now = datetime.now(UTC)
    alarm = Alarm.create(now + timedelta(minutes=1), 'UTC', 'Tea', now)
    dialog = AlarmNotification(alarm, {'sound': {'enabled': True}})
    qtbot.addWidget(dialog)
    dialog.show()
    assert 'Audio unavailable' in dialog.audio_status.text()
    QTest.keyClick(dialog, Qt.Key_Return)
    assert not dialog.isVisible()
    assert not dialog.flash_timer.isActive()


def test_storage_worker_does_not_block_gui_and_recovers(qtbot, tmp_path, monkeypatch):
    from threading import Event
    from PyQt5.QtCore import QTimer
    config = AppConfig.load(tmp_path / 'config.yaml')
    entered, release = Event(), Event()
    original = AlarmStore.transact
    calls = []
    def delayed(self, *args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            entered.set()
            if not release.wait(5):
                raise TimeoutError('test release timed out')
            raise OSError('simulated storage error')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(AlarmStore, 'transact', delayed)
    controller = AlarmController(config)
    errors, beats = [], []
    controller.error.connect(errors.append)
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: beats.append(True))
    heartbeat.start(5)
    try:
        qtbot.waitUntil(entered.is_set)
        qtbot.waitUntil(lambda: len(beats) >= 3)
        release.set()
        qtbot.waitUntil(lambda: bool(errors))
        qtbot.waitUntil(lambda: not controller.startup)
        assert 'simulated storage error' in errors[0]
    finally:
        heartbeat.stop()
        release.set()
        controller.stop()
        qtbot.waitUntil(lambda: not controller.thread.isRunning())
