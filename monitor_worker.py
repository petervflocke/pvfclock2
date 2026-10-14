from __future__ import annotations

import logging
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from metrics_provider import SystemMetricsProvider


logger = logging.getLogger(__name__)


class MonitorWorker(QObject):
    """Own the stateful provider and collect without touching GUI objects."""

    completed = pyqtSignal(int, object)

    def __init__(self, provider: SystemMetricsProvider | None = None):
        super().__init__()
        self._provider = provider

    @pyqtSlot(int, object, bool)
    def collect(self, generation: int, config: dict[str, Any], refresh: bool) -> None:
        metrics = None
        try:
            if self._provider is None:
                self._provider = SystemMetricsProvider(config=config)
            self._provider.config = config
            if refresh:
                self._provider.force_external_ip_refresh()
            metrics = self._provider.collect()
        except Exception:
            logger.exception("Monitor collection failed; retrying on the next poll")
        finally:
            self.completed.emit(generation, metrics)
