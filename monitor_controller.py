from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
import logging
from typing import Any

from PyQt5.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot

from metrics_provider import MetricValue, SystemMetricsProvider
from monitor_worker import MonitorWorker


logger = logging.getLogger(__name__)


def history_capacity(update_interval_seconds: float, history_minutes: float) -> int:
    if update_interval_seconds <= 0 or history_minutes <= 0:
        return 1
    return max(1, int(history_minutes * 60 / update_interval_seconds))


@dataclass
class HistoryBuffer:
    capacity: int
    values: deque[float] = field(init=False)

    def __post_init__(self) -> None:
        self.values = deque(maxlen=max(1, self.capacity))

    def append(self, value: float | None) -> None:
        if value is not None:
            self.values.append(float(value))

    def as_list(self) -> list[float]:
        return list(self.values)


class MonitorController(QObject):
    collection_requested = pyqtSignal(int, object, bool)
    shutdown_finished = pyqtSignal()

    def __init__(
        self,
        app_config: Any,
        panel: Any,
        provider: SystemMetricsProvider | None = None,
    ):
        super().__init__()
        self.app_config = app_config
        self.panel = panel
        self._busy = False
        self._closing = False
        self._pending_refresh = False
        self._pending_poll = False
        self._generation = 0
        self.thread = QThread(self)
        self.worker = MonitorWorker(provider)
        self.worker.moveToThread(self.thread)
        self.collection_requested.connect(self.worker.collect, Qt.QueuedConnection)
        self.worker.completed.connect(self._collection_completed, Qt.QueuedConnection)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.shutdown_finished)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._timer_poll)
        self.configure(app_config)
        self.thread.start()

    def configure(self, app_config: Any) -> None:
        if self._closing:
            return
        was_active = getattr(self, "timer", None) is not None and self.timer.isActive()
        if was_active:
            self.timer.stop()
        self.update_interval_seconds = float(app_config.get("app.update_interval_seconds", 5))
        self.collect_history_mode = str(app_config.get("app.collect_history.mode", "always"))
        self.capacity = history_capacity(
            self.update_interval_seconds,
            float(app_config.get("app.collect_history.history_minutes", 5)),
        )
        if not hasattr(self, "history"):
            self.history: dict[str, HistoryBuffer] = {}
        else:
            self._resize_history_buffers()
        self.app_config = app_config
        self._config_snapshot = deepcopy(app_config.data)
        self._generation += 1
        if self._busy:
            self._pending_poll = True
        self.timer.setInterval(max(1, int(self.update_interval_seconds * 1000)))
        if was_active:
            self.timer.start()

    def start(self) -> None:
        if self._closing:
            return
        self.poll()
        self.timer.start()

    def stop(self) -> None:
        """Permanently stop; emit shutdown_finished after active work exits."""
        if self._closing:
            return
        self._closing = True
        self.timer.stop()
        self._pending_poll = False
        self._pending_refresh = False
        if not self._busy:
            self.thread.quit()

    def poll(self) -> None:
        """Request an immediate refresh, coalescing requests during active work."""
        self._request_poll(explicit=True)

    @pyqtSlot()
    def _timer_poll(self) -> None:
        self._request_poll(explicit=False)

    def _request_poll(self, explicit: bool) -> None:
        if self._closing:
            return
        if self.collect_history_mode == "panel_visible" and not self.panel.isVisible():
            return
        if self._busy:
            self._pending_poll = self._pending_poll or explicit
            return
        self._busy = True
        refresh = self._pending_refresh
        self._pending_refresh = False
        self._pending_poll = False
        self.collection_requested.emit(self._generation, deepcopy(self._config_snapshot), refresh)

    @pyqtSlot(int, object)
    def _collection_completed(self, generation: int, metrics: list[MetricValue] | None) -> None:
        try:
            visible_mode_hidden = (
                self.collect_history_mode == "panel_visible" and not self.panel.isVisible()
            )
            if (
                not self._closing
                and generation == self._generation
                and metrics is not None
                and not visible_mode_hidden
            ):
                for metric in metrics:
                    self._history_for(metric.key).append(metric.value)
                history = {key: buffer.as_list() for key, buffer in self.history.items()}
                self.panel.set_metrics(metrics, history)
        except Exception:
            logger.exception("Monitor display update failed; retrying on the next poll")
        finally:
            self._busy = False
            if self._closing:
                self.thread.quit()
            elif self._pending_poll:
                self._request_poll(explicit=True)

    def refresh_external_ip(self) -> None:
        if self._closing:
            return
        self._pending_refresh = True
        self.poll()

    def _history_for(self, key: str) -> HistoryBuffer:
        if key not in self.history:
            self.history[key] = HistoryBuffer(self.capacity)
        return self.history[key]

    def _resize_history_buffers(self) -> None:
        for key, buffer in list(self.history.items()):
            resized = HistoryBuffer(self.capacity)
            for value in buffer.as_list()[-self.capacity:]:
                resized.append(value)
            self.history[key] = resized
