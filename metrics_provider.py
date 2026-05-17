from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import time
from typing import Any, Callable

from app_config import DEFAULT_CONFIG
from sensors_parser import SensorReading, parse_sensors_output

try:
    import psutil
except ImportError:
    psutil = None


@dataclass(frozen=True)
class MetricValue:
    key: str
    label: str
    value: float | None
    display_value: str
    unit: str
    available: bool


class SystemMetricsProvider:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        psutil_module: Any = psutil,
        loadavg_func: Callable[[], tuple[float, float, float]] = os.getloadavg,
        run_command: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        time_func: Callable[[], float] = time.monotonic,
        sensors_timeout_seconds: float = 2.0,
    ):
        self.config = config or DEFAULT_CONFIG
        self.psutil = psutil_module
        self.loadavg_func = loadavg_func
        self.run_command = run_command
        self.time_func = time_func
        self.sensors_timeout_seconds = sensors_timeout_seconds
        self._last_network_sample: tuple[float, dict[str, tuple[int, int]]] | None = None

    def collect(self) -> list[MetricValue]:
        values: list[MetricValue] = []
        if self._enabled("metrics.system_load"):
            values.append(self.system_load())
        if self._enabled("metrics.cpu"):
            values.append(self.cpu_percent())
        if self._enabled("metrics.memory"):
            values.append(self.memory())
        if self._enabled("metrics.temperatures"):
            values.extend(self.temperatures())
        if self._enabled("metrics.network"):
            values.extend(self.network())
        return values

    def system_load(self) -> MetricValue:
        label = str(self._get("metrics.system_load.label", "System Load"))
        try:
            load_1m = float(self.loadavg_func()[0])
        except (AttributeError, OSError, IndexError, TypeError, ValueError) as error:
            return self._unavailable("system_load", label, "", error)

        return MetricValue(
            key="system_load",
            label=label,
            value=load_1m,
            display_value=f"{load_1m:.2f}",
            unit="",
            available=True,
        )

    def cpu_percent(self) -> MetricValue:
        label = str(self._get("metrics.cpu.label", "CPU"))
        if self.psutil is None:
            return self._unavailable("cpu", label, "%", "psutil unavailable")

        try:
            value = float(self.psutil.cpu_percent(interval=None))
        except Exception as error:
            return self._unavailable("cpu", label, "%", error)

        return MetricValue(
            key="cpu",
            label=label,
            value=value,
            display_value=f"{value:.0f}%",
            unit="%",
            available=True,
        )

    def memory(self) -> MetricValue:
        label = str(self._get("metrics.memory.label", "Memory"))
        mode = str(self._get("metrics.memory.mode", "used_percent"))
        if self.psutil is None:
            return self._unavailable("memory", label, "%", "psutil unavailable")

        try:
            memory = self.psutil.virtual_memory()
        except Exception as error:
            return self._unavailable("memory", label, "%", error)

        if mode == "available":
            value = float(memory.available)
            display_value = _format_bytes(value)
            unit = "B"
        elif mode == "used":
            value = float(memory.used)
            display_value = _format_bytes(value)
            unit = "B"
        else:
            value = float(memory.percent)
            display_value = f"{value:.0f}%"
            unit = "%"

        return MetricValue(
            key="memory",
            label=label,
            value=value,
            display_value=display_value,
            unit=unit,
            available=True,
        )

    def temperatures(self) -> list[MetricValue]:
        command = str(self._get("metrics.temperatures.command", "sensors"))
        try:
            result = self.run_command(
                [command],
                capture_output=True,
                text=True,
                timeout=self.sensors_timeout_seconds,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as error:
            return [self._unavailable("temperatures", "Temperatures", "C", error)]

        if result.returncode != 0:
            return [self._unavailable("temperatures", "Temperatures", "C", result.stderr.strip())]

        readings = parse_sensors_output(result.stdout)
        return self._configured_temperature_values(readings)

    def _configured_temperature_values(self, readings: list[SensorReading]) -> list[MetricValue]:
        values: list[MetricValue] = []
        readings_by_key = {(reading.chip, reading.feature): reading for reading in readings}
        chips = self._get("metrics.temperatures.chips", {})
        if not isinstance(chips, dict):
            return values

        for chip_name, chip_config in chips.items():
            if not isinstance(chip_config, dict) or not chip_config.get("enabled", False):
                continue

            features = chip_config.get("features", {})
            if not isinstance(features, dict):
                continue

            for feature_name, feature_config in features.items():
                if not isinstance(feature_config, dict) or not feature_config.get("enabled", False):
                    continue
                reading = readings_by_key.get((str(chip_name), str(feature_name)))
                if reading is None:
                    continue
                label = str(feature_config.get("label") or chip_config.get("label") or feature_name)
                values.append(
                    MetricValue(
                        key=f"temperature.{chip_name}.{feature_name}",
                        label=label,
                        value=reading.value,
                        display_value=f"{reading.value:.1f} {reading.unit}",
                        unit=reading.unit,
                        available=True,
                    )
                )

        return values

    def network(self) -> list[MetricValue]:
        if self.psutil is None:
            return [self._unavailable("network", "Network", "B/s", "psutil unavailable")]

        try:
            counters = self.psutil.net_io_counters(pernic=True)
        except Exception as error:
            return [self._unavailable("network", "Network", "B/s", error)]

        now = float(self.time_func())
        current = {
            str(interface): (int(counter.bytes_recv), int(counter.bytes_sent))
            for interface, counter in counters.items()
        }
        previous = self._last_network_sample
        self._last_network_sample = (now, current)

        elapsed = 0.0
        previous_values: dict[str, tuple[int, int]] = {}
        if previous is not None:
            previous_time, previous_values = previous
            elapsed = max(0.0, now - previous_time)

        values: list[MetricValue] = []
        interfaces = self._get("metrics.network.interfaces", {})
        if not isinstance(interfaces, dict):
            return values

        for interface_name, interface_config in interfaces.items():
            if not isinstance(interface_config, dict) or not interface_config.get("enabled", False):
                continue
            interface_key = str(interface_name)
            current_counts = current.get(interface_key)
            previous_counts = previous_values.get(interface_key)
            if current_counts is None:
                continue

            features = interface_config.get("features", {})
            if not isinstance(features, dict):
                continue

            for feature_name, feature_config in features.items():
                if not isinstance(feature_config, dict) or not feature_config.get("enabled", False):
                    continue
                direction = str(feature_name).lower()
                if direction not in ("rx", "tx"):
                    continue
                counter_index = 0 if direction == "rx" else 1
                rate = 0.0
                if previous_counts is not None and elapsed > 0:
                    delta = max(0, current_counts[counter_index] - previous_counts[counter_index])
                    rate = delta / elapsed
                label = str(feature_config.get("label") or f"{interface_config.get('label') or interface_key} {direction.upper()}")
                values.append(
                    MetricValue(
                        key=f"network.{interface_key}.{direction}",
                        label=label,
                        value=rate,
                        display_value=f"{_format_bytes(rate)}/s",
                        unit="B/s",
                        available=True,
                    )
                )

        return values

    def _enabled(self, dotted_key: str) -> bool:
        return bool(self._get(f"{dotted_key}.enabled", False))

    def _get(self, dotted_key: str, default: object | None = None) -> object:
        current: object = self.config
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def _unavailable(key: str, label: str, unit: str, error: object) -> MetricValue:
        return MetricValue(
            key=key,
            label=label,
            value=None,
            display_value="n/a",
            unit=unit,
            available=False,
        )


def _format_bytes(value: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = value
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TiB"
