from __future__ import annotations

from dataclasses import asdict
import logging

from PyQt5.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot

from alarm_model import Alarm
from alarm_store import AlarmStore
from app_config import AppConfig


class AlarmWorker(QObject):
    finished = pyqtSignal(object, bool, object, str)
    config_finished = pyqtSignal(object, str, object)

    @pyqtSlot(object, str, object, bool)
    def execute(self, path, action, payload, startup):
        if action in ('reload', 'geometry'):
            try:
                config = AppConfig.load(path)
                if action == 'geometry':
                    config.data["clock"]["geometry"].update(
                        {key: int(payload[key]) for key in ("x", "y", "w", "h")}
                    )
                    config.save()
                self.config_finished.emit(config, action, None)
            except Exception as error:
                self.config_finished.emit(None, action, error)
            return
        try:
            alarm, fired, settings = AlarmStore(path).transact(action, payload, startup)
            self.finished.emit(alarm, fired, settings, '')
        except Exception as error:
            logging.getLogger(__name__).exception('Alarm operation failed')
            self.finished.emit(None, False, {}, str(error))


class AlarmController(QObject):
    request = pyqtSignal(object, str, object, bool)
    changed = pyqtSignal(object)
    ringing = pyqtSignal(object, object)
    error = pyqtSignal(str)
    shutdown_finished = pyqtSignal()
    configuration_ready = pyqtSignal(object, str, object)

    def __init__(self, config: AppConfig, parent: QObject | None = None):
        super().__init__(parent)
        self.config = config
        self.current = None
        self.busy = False
        self.pending = []
        self.closing = False
        self.startup = True
        self.thread = QThread(self)
        self.worker = AlarmWorker()
        self.worker.moveToThread(self.thread)
        self.request.connect(self.worker.execute, Qt.QueuedConnection)
        self.worker.finished.connect(self.completed)
        self.worker.config_finished.connect(self.config_completed)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.shutdown_finished)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.poll)
        self.thread.start()
        self.timer.start()
        QTimer.singleShot(0, self.poll)

    def configure(self, config: AppConfig) -> None:
        self.config = config
        self.poll()

    def poll(self) -> None:
        self.submit('poll')

    def submit(self, action: str, payload: object = None) -> None:
        if self.closing:
            return
        if self.config.temporary and action != 'reload':
            self.current = None
            self.changed.emit(None)
            if action != 'poll':
                self.error.emit('Fix the YAML and reload before setting an alarm.')
            return
        if self.busy:
            if action != 'poll':
                self.pending.append((action, payload))
            return
        self.busy = True
        self.request.emit(self.config.path, action, payload, self.startup)

    def arm(self, alarm: Alarm) -> None:
        self.submit('set', asdict(alarm))

    def cancel(self) -> None:
        if self.current:
            self.submit('cancel', self.current.id)

    def drain_pending(self) -> None:
        if self.pending and not self.closing:
            action, payload = self.pending.pop(0)
            self.submit(action, payload)

    @pyqtSlot(object, str, object)
    def config_completed(self, config, action, error):
        self.busy = False
        if self.closing:
            self.thread.quit()
            return
        self.configuration_ready.emit(config, action, error)
        self.drain_pending()

    @pyqtSlot(object, bool, object, str)
    def completed(self, alarm, fired, settings, error):
        self.busy = False
        if self.closing:
            self.thread.quit()
            return
        if error:
            self.error.emit(error)
        else:
            self.startup = False
            self.current = alarm
            self.changed.emit(alarm)
            if fired:
                self.ringing.emit(alarm, settings)
        self.drain_pending()

    def stop(self) -> None:
        self.closing = True
        self.pending.clear()
        self.timer.stop()
        if not self.busy:
            self.thread.quit()
