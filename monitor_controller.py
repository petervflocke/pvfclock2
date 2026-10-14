from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from PyQt5.QtCore import QTimer

from metrics_provider import MetricValue, SystemMetricsProvider


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


class MonitorController:
    def __init__(
        self,
        app_config: Any,
        panel: Any,
        provider: SystemMetricsProvider | None = None,
    ):
        self.app_config = app_config
        self.panel = panel
        self.provider = provider or SystemMetricsProvider(config=app_config.data)
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.configure(app_config)

    def configure(self, app_config: Any) -> None:
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
        self.provider.config = app_config.data
        self.timer.setInterval(max(1, int(self.update_interval_seconds * 1000)))
        if was_active:
            self.timer.start()

    def start(self) -> None:
        self.poll()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def poll(self) -> None:
        if self.collect_history_mode == "panel_visible" and not self.panel.isVisible():
            return

        metrics = self.provider.collect()
        for metric in metrics:
            self._history_for(metric.key).append(metric.value)

        history = {key: buffer.as_list() for key, buffer in self.history.items()}
        self.panel.set_metrics(metrics, history)

    def refresh_external_ip(self) -> None:
        self.provider.force_external_ip_refresh()
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
