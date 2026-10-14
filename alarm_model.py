from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import os
import re
import uuid

UTC = timezone.utc


def local_zone() -> ZoneInfo:
    name = os.environ.get("TZ", "").lstrip(":")
    if not name:
        target = str(Path('/etc/localtime').resolve())
        if '/zoneinfo/' in target:
            name = target.split('/zoneinfo/', 1)[1]
        elif Path('/etc/timezone').exists():
            name = Path('/etc/timezone').read_text().strip()
    return ZoneInfo(name or 'UTC')


def parse_time(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{2}):?(\d{2})", text.strip())
    if not match:
        raise ValueError("Enter HH:MM or HHMM, for example 14:30.")
    hour, minute = map(int, match.groups())
    if hour > 23 or minute > 59:
        raise ValueError("Hours must be 00–23 and minutes 00–59.")
    return hour, minute


def resolve_local(naive: datetime, zone: ZoneInfo) -> list[datetime]:
    """Return zero (DST gap), one, or two (DST fold) distinct UTC instants."""
    candidates = set()
    for fold in (0, 1):
        instant = naive.replace(tzinfo=zone, fold=fold).astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == naive:
            candidates.add(instant)
    return sorted(candidates)


@dataclass(frozen=True)
class Alarm:
    id: str
    scheduled_at: str
    timezone: str
    label: str
    state: str
    state_changed_at: str

    @property
    def due(self) -> datetime:
        return datetime.fromisoformat(self.scheduled_at).astimezone(UTC)

    @classmethod
    def create(cls, instant: datetime, zone: str, label: str, now: datetime) -> Alarm:
        if instant.tzinfo is None or instant <= now:
            raise ValueError("Choose a future alarm time.")
        ZoneInfo(zone)
        return cls(str(uuid.uuid4()), instant.astimezone(UTC).isoformat(), zone,
                   label.strip(), 'armed', now.astimezone(UTC).isoformat())

    @classmethod
    def from_dict(cls, data: object) -> Alarm | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise ValueError("Invalid alarm record: expected a mapping.")
        try:
            alarm = cls(**data)
            if not all(isinstance(v, str) for v in asdict(alarm).values()):
                raise ValueError("Alarm fields must be strings")
            if not alarm.id or alarm.state not in {'armed', 'fired', 'cancelled', 'missed'}:
                raise ValueError("Invalid alarm ID or state")
            for value in (alarm.scheduled_at, alarm.state_changed_at):
                if datetime.fromisoformat(value).tzinfo is None:
                    raise ValueError("Alarm timestamps need timezone offsets")
            ZoneInfo(alarm.timezone)
            return alarm
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError(f"Invalid alarm record: {error}") from error

    def evaluate(self, now: datetime, startup: bool, tolerance: float) -> Alarm:
        if self.state != 'armed' or now < self.due:
            return self
        state = 'missed' if startup or (now - self.due).total_seconds() > tolerance else 'fired'
        return replace(self, state=state, state_changed_at=now.astimezone(UTC).isoformat())
