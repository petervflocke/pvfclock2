from __future__ import annotations

from pathlib import Path

from sensors_parser import SensorReading, parse_sensors_output


def _readings_by_chip_feature() -> dict[tuple[str, str], SensorReading]:
    output = Path("sensors.txt").read_text(encoding="utf-8")
    return {(reading.chip, reading.feature): reading for reading in parse_sensors_output(output)}


def test_parse_k10temp_tctl_temperature() -> None:
    readings = _readings_by_chip_feature()

    reading = readings[("k10temp-pci-00c3", "Tctl")]

    assert reading.adapter == "PCI adapter"
    assert reading.value == 49.9
    assert reading.unit == "C"


def test_parse_amdgpu_edge_temperature() -> None:
    readings = _readings_by_chip_feature()

    reading = readings[("amdgpu-pci-c400", "edge")]

    assert reading.adapter == "PCI adapter"
    assert reading.value == 42.0
    assert reading.unit == "C"


def test_parse_nvme_composite_temperature() -> None:
    readings = _readings_by_chip_feature()

    reading = readings[("nvme-pci-0300", "Composite")]

    assert reading.adapter == "PCI adapter"
    assert reading.value == 33.9
    assert reading.unit == "C"


def test_ignored_non_temperature_values() -> None:
    output = """
amdgpu-pci-c400
Adapter: PCI adapter
vddgfx:        1.18 V  
vddnb:       758.00 mV 
edge:         +42.0°C  
PPT:          10.02 W  (avg =  11.15 W)
""".lstrip()

    readings = parse_sensors_output(output)

    assert readings == [
        SensorReading(
            chip="amdgpu-pci-c400",
            adapter="PCI adapter",
            feature="edge",
            value=42.0,
            unit="C",
        )
    ]


def test_malformed_lines_do_not_raise() -> None:
    output = """
k10temp-pci-00c3
Adapter: PCI adapter
Tctl:         nope
Malformed line with no meaning
broken:       +not-a-number°C

nvme-pci-0300
Adapter: PCI adapter
Composite:    -5.5°C
""".lstrip()

    readings = parse_sensors_output(output)

    assert readings == [
        SensorReading(
            chip="nvme-pci-0300",
            adapter="PCI adapter",
            feature="Composite",
            value=-5.5,
            unit="C",
        )
    ]
