from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
import time
from typing import Any, Callable
from urllib.request import urlopen

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
        external_ip_fetcher: Callable[[float], dict[str, Any]] | None = None,
        sensors_timeout_seconds: float = 2.0,
    ):
        self.config = config or DEFAULT_CONFIG
        self.psutil = psutil_module
        self.loadavg_func = loadavg_func
        self.run_command = run_command
        self.time_func = time_func
        self.external_ip_fetcher = external_ip_fetcher or _fetch_external_ip
        self.sensors_timeout_seconds = sensors_timeout_seconds
        self._last_network_sample: tuple[float, dict[str, tuple[int, int]]] | None = None
        self._external_ip_cache: dict[str, Any] | None = None
        self._external_ip_cache_time = 0.0
        self._external_ip_route_interface: str | None = None
        self._force_external_ip_refresh = False

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
        if self._enabled("metrics.external_ip"):
            values.append(self.external_ip())
        return values

    def force_external_ip_refresh(self) -> None:
        self._force_external_ip_refresh = True

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

    def external_ip(self) -> MetricValue:
        label = str(self._get("metrics.external_ip.label", "WAN"))
        now = float(self.time_func())
        route_interface = self._default_route_interface()
        refresh_seconds = float(self._get("metrics.external_ip.refresh_seconds", 3600))
        timeout_seconds = float(self._get("metrics.external_ip.timeout_seconds", 3))
        refresh_on_route_change = bool(self._get("metrics.external_ip.refresh_on_route_change", True))
        route_changed = (
            refresh_on_route_change
            and route_interface is not None
            and route_interface != self._external_ip_route_interface
        )
        stale = self._external_ip_cache is None or now - self._external_ip_cache_time >= refresh_seconds

        if self._force_external_ip_refresh or route_changed or stale:
            self._force_external_ip_refresh = False
            try:
                self._external_ip_cache = self.external_ip_fetcher(timeout_seconds)
                self._external_ip_cache_time = now
                self._external_ip_route_interface = route_interface
            except Exception as error:
                if self._external_ip_cache is None:
                    return self._unavailable("external_ip", label, "", error)
                self._external_ip_cache_time = now
                self._external_ip_route_interface = route_interface

        if self._external_ip_cache is None:
            return self._unavailable("external_ip", label, "", "external IP unavailable")

        ip_address = str(self._external_ip_cache.get("ip") or "n/a")
        country_code = str(self._external_ip_cache.get("country_code") or "").upper()
        country = str(self._external_ip_cache.get("country") or country_code)
        display_parts = [ip_address]
        if country_code:
            display_parts.append(country_code)

        expected_country = self._expected_country_for_interface(route_interface)
        mismatch = (
            expected_country is not None
            and country_code
            and country_code.upper() != expected_country.upper()
        )
        return MetricValue(
            key="external_ip",
            label=label,
            value=1.0 if mismatch else 0.0,
            display_value=" ".join(display_parts) if display_parts else country,
            unit="",
            available=True,
        )

    def _default_route_interface(self) -> str | None:
        try:
            result = self.run_command(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            parts = line.split()
            if "dev" not in parts:
                continue
            dev_index = parts.index("dev")
            if dev_index + 1 < len(parts):
                return parts[dev_index + 1]
        return None

    def _expected_country_for_interface(self, interface_name: str | None) -> str | None:
        if interface_name is None:
            return None
        expected = self._get("metrics.external_ip.alarm.expected_by_interface", {})
        if not isinstance(expected, dict):
            return None
        country_code = expected.get(interface_name)
        if country_code is None:
            return None
        return str(country_code)

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


def _fetch_external_ip(timeout_seconds: float) -> dict[str, Any]:
    with urlopen("https://ipwho.is/", timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise ValueError("external IP lookup failed")
    flag = ""
    flag_data = payload.get("flag")
    if isinstance(flag_data, dict):
        flag = str(flag_data.get("emoji") or "")
    return {
        "ip": payload.get("ip"),
        "country": payload.get("country"),
        "country_code": payload.get("country_code"),
        "flag": flag,
    }


def _flag_for_country_code(country_code: str) -> str:
    if len(country_code) != 2 or not country_code.isalpha():
        return ""
    base = 0x1F1E6
    return "".join(chr(base + ord(letter.upper()) - ord("A")) for letter in country_code)
