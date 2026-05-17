from __future__ import annotations

from dataclasses import dataclass
import re


TEMPERATURE_RE = re.compile(r"^(?P<feature>[^:]+):\s*(?P<value>[+-]?\d+(?:\.\d+)?)\s*°(?P<unit>C)\b")


@dataclass(frozen=True)
class SensorReading:
    chip: str
    adapter: str | None
    feature: str
    value: float
    unit: str


def parse_sensors_output(output: str) -> list[SensorReading]:
    readings: list[SensorReading] = []
    current_chip: str | None = None
    current_adapter: str | None = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            current_chip = None
            current_adapter = None
            continue

        if line.startswith("Adapter:"):
            current_adapter = line.split(":", 1)[1].strip()
            continue

        match = TEMPERATURE_RE.match(line)
        if match and current_chip:
            readings.append(
                SensorReading(
                    chip=current_chip,
                    adapter=current_adapter,
                    feature=match.group("feature").strip(),
                    value=float(match.group("value")),
                    unit=match.group("unit"),
                )
            )
            continue

        if ":" not in line and not line.startswith("("):
            current_chip = line
            current_adapter = None

    return readings
