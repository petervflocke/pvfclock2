from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
from types import SimpleNamespace

from app_config import DEFAULT_CONFIG
from metrics_provider import MetricValue, SystemMetricsProvider


class FakePsutil:
    @staticmethod
    def cpu_percent(interval=None) -> float:
        assert interval is None
        return 12.4

    @staticmethod
    def virtual_memory() -> SimpleNamespace:
        return SimpleNamespace(
            percent=41.2,
            available=8 * 1024**3,
            used=6 * 1024**3,
        )

    @staticmethod
    def net_io_counters(pernic=False) -> dict[str, SimpleNamespace]:
        assert pernic is True
        return {
            "enp1s0": SimpleNamespace(bytes_recv=1024, bytes_sent=2048),
            "wlp2s0": SimpleNamespace(bytes_recv=4096, bytes_sent=8192),
        }


def test_format_system_load() -> None:
    provider = SystemMetricsProvider(loadavg_func=lambda: (0.715, 0.3, 0.2))

    metric = provider.system_load()

    assert metric == MetricValue(
        key="system_load",
        label="System Load",
        value=0.715,
        display_value="0.71",
        unit="",
        available=True,
    )


def test_format_cpu_percent() -> None:
    provider = SystemMetricsProvider(psutil_module=FakePsutil)

    metric = provider.cpu_percent()

    assert metric.key == "cpu"
    assert metric.label == "CPU"
    assert metric.value == 12.4
    assert metric.display_value == "12%"
    assert metric.unit == "%"
    assert metric.available is True


def test_format_memory_used_percent() -> None:
    provider = SystemMetricsProvider(psutil_module=FakePsutil)

    metric = provider.memory()

    assert metric.key == "memory"
    assert metric.value == 41.2
    assert metric.display_value == "41%"
    assert metric.unit == "%"
    assert metric.available is True


def test_format_memory_available_bytes() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["memory"]["mode"] = "available"
    provider = SystemMetricsProvider(config=config, psutil_module=FakePsutil)

    metric = provider.memory()

    assert metric.value == float(8 * 1024**3)
    assert metric.display_value == "8.0 GiB"
    assert metric.unit == "B"
    assert metric.available is True


def test_missing_psutil_returns_unavailable() -> None:
    provider = SystemMetricsProvider(psutil_module=None)

    assert provider.cpu_percent() == MetricValue(
        key="cpu",
        label="CPU",
        value=None,
        display_value="n/a",
        unit="%",
        available=False,
    )
    assert provider.memory() == MetricValue(
        key="memory",
        label="Memory",
        value=None,
        display_value="n/a",
        unit="%",
        available=False,
    )


def test_temperatures_use_sensors_command_with_timeout() -> None:
    calls = []
    output = Path("sensors.txt").read_text(encoding="utf-8")

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=output, stderr="")

    provider = SystemMetricsProvider(run_command=fake_run, sensors_timeout_seconds=1.5)

    provider.temperatures()

    assert calls == [
        (
            (["sensors"],),
            {
                "capture_output": True,
                "text": True,
                "timeout": 1.5,
            },
        )
    ]


def test_configured_temperature_values_are_returned_by_label() -> None:
    output = Path("sensors.txt").read_text(encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=output, stderr="")

    provider = SystemMetricsProvider(run_command=fake_run)

    metrics = provider.temperatures()

    assert metrics == [
        MetricValue(
            key="temperature.k10temp-pci-00c3.Tctl",
            label="CPU",
            value=49.9,
            display_value="49.9 C",
            unit="C",
            available=True,
        ),
        MetricValue(
            key="temperature.amdgpu-pci-c400.edge",
            label="GPU",
            value=42.0,
            display_value="42.0 C",
            unit="C",
            available=True,
        ),
        MetricValue(
            key="temperature.nvme-pci-0300.Composite",
            label="NVMe",
            value=33.9,
            display_value="33.9 C",
            unit="C",
            available=True,
        ),
    ]


def test_configured_missing_sensor_is_skipped() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["temperatures"]["chips"]["missing-chip"] = {
        "enabled": True,
        "label": "Missing",
        "features": {"temp1": {"enabled": True, "label": "Missing"}},
    }
    output = """
k10temp-pci-00c3
Adapter: PCI adapter
Tctl:         +49.9°C
""".lstrip()

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=output, stderr="")

    provider = SystemMetricsProvider(config=config, run_command=fake_run)

    metrics = provider.temperatures()

    assert metrics == [
        MetricValue(
            key="temperature.k10temp-pci-00c3.Tctl",
            label="CPU",
            value=49.9,
            display_value="49.9 C",
            unit="C",
            available=True,
        )
    ]


def test_temperature_output_order_follows_config_order() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["temperatures"]["chips"] = {
        "spd5118-i2c-16-50": {
            "enabled": True,
            "label": "DIMM 1",
            "features": {
                "temp1": {
                    "enabled": True,
                    "label": "DIMM 1",
                },
            },
        },
        "k10temp-pci-00c3": {
            "enabled": True,
            "label": "CPU",
            "features": {
                "Tctl": {
                    "enabled": True,
                    "label": "CPU",
                },
            },
        },
    }
    output = Path("sensors.txt").read_text(encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=output, stderr="")

    provider = SystemMetricsProvider(config=config, run_command=fake_run)

    metrics = provider.temperatures()

    assert metrics == [
        MetricValue(
            key="temperature.spd5118-i2c-16-50.temp1",
            label="DIMM 1",
            value=40.8,
            display_value="40.8 C",
            unit="C",
            available=True,
        ),
        MetricValue(
            key="temperature.k10temp-pci-00c3.Tctl",
            label="CPU",
            value=49.9,
            display_value="49.9 C",
            unit="C",
            available=True,
        ),
    ]


def test_missing_sensors_command_returns_unavailable() -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("sensors")

    provider = SystemMetricsProvider(run_command=fake_run)

    assert provider.temperatures() == [
        MetricValue(
            key="temperatures",
            label="Temperatures",
            value=None,
            display_value="n/a",
            unit="C",
            available=False,
        )
    ]


def test_collect_respects_disabled_metrics() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["cpu"]["enabled"] = False
    config["metrics"]["memory"]["enabled"] = False
    config["metrics"]["temperatures"]["enabled"] = False
    provider = SystemMetricsProvider(
        config=config,
        psutil_module=FakePsutil,
        loadavg_func=lambda: (1.0, 2.0, 3.0),
    )

    metrics = provider.collect()

    assert [metric.key for metric in metrics] == ["system_load"]


def test_network_first_sample_returns_zero_rates() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["network"] = {
        "enabled": True,
        "interfaces": {
            "enp1s0": {
                "enabled": True,
                "label": "LAN",
                "features": {
                    "rx": {"enabled": True, "label": "LAN RX"},
                    "tx": {"enabled": True, "label": "LAN TX"},
                },
            }
        },
    }
    provider = SystemMetricsProvider(config=config, psutil_module=FakePsutil, time_func=lambda: 10.0)

    metrics = provider.network()

    assert metrics == [
        MetricValue(
            key="network.enp1s0.rx",
            label="LAN RX",
            value=0.0,
            display_value="0.0 B/s",
            unit="B/s",
            available=True,
        ),
        MetricValue(
            key="network.enp1s0.tx",
            label="LAN TX",
            value=0.0,
            display_value="0.0 B/s",
            unit="B/s",
            available=True,
        ),
    ]


def test_network_rates_are_delta_bytes_per_second() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["network"] = {
        "enabled": True,
        "interfaces": {
            "enp1s0": {
                "enabled": True,
                "label": "LAN",
                "features": {
                    "rx": {"enabled": True, "label": "LAN RX"},
                    "tx": {"enabled": True, "label": "LAN TX"},
                },
            }
        },
    }
    samples = [
        {"enp1s0": SimpleNamespace(bytes_recv=1_000, bytes_sent=2_000)},
        {"enp1s0": SimpleNamespace(bytes_recv=3_048, bytes_sent=4_048)},
    ]
    times = [10.0, 12.0]

    class FakeNetworkPsutil:
        @staticmethod
        def net_io_counters(pernic=False):
            assert pernic is True
            return samples.pop(0)

    provider = SystemMetricsProvider(
        config=config,
        psutil_module=FakeNetworkPsutil,
        time_func=lambda: times.pop(0),
    )

    provider.network()
    metrics = provider.network()

    assert metrics == [
        MetricValue(
            key="network.enp1s0.rx",
            label="LAN RX",
            value=1024.0,
            display_value="1.0 KiB/s",
            unit="B/s",
            available=True,
        ),
        MetricValue(
            key="network.enp1s0.tx",
            label="LAN TX",
            value=1024.0,
            display_value="1.0 KiB/s",
            unit="B/s",
            available=True,
        ),
    ]


def test_network_missing_interface_is_skipped() -> None:
    config = deepcopy(DEFAULT_CONFIG)
    config["metrics"]["network"] = {
        "enabled": True,
        "interfaces": {
            "missing0": {
                "enabled": True,
                "features": {"rx": {"enabled": True}},
            }
        },
    }
    provider = SystemMetricsProvider(config=config, psutil_module=FakePsutil)

    assert provider.network() == []
