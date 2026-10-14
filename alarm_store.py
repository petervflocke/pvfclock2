from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

from alarm_model import Alarm, UTC
from app_config import AppConfig
from config_storage import atomic_write, config_lock


class AlarmStore:
    def __init__(self, path: Path):
        self.path = path

    def transact(self, action: str = 'poll', payload: object = None,
                 startup: bool = False, now: datetime | None = None) -> tuple[Alarm | None, bool, dict]:
        now = now or datetime.now(UTC)
        with config_lock(self.path):
            config = AppConfig._load_unlocked(self.path)
            settings = config.get('alarm')
            if not isinstance(settings, dict):
                raise ValueError('Invalid alarm settings: expected a mapping')
            current = Alarm.from_dict(settings.get('current'))
            updated = current
            if action == 'set':
                updated = Alarm.from_dict(payload)
                if updated is None or updated.state != 'armed' or updated.due <= now:
                    raise ValueError('Choose a future alarm time.')
            elif action == 'cancel':
                if current and current.id == payload and current.state == 'armed':
                    updated = replace(current, state='cancelled', state_changed_at=now.isoformat())
            elif action == 'poll' and current:
                tolerance = max(0, min(10, float(settings.get('lateness_tolerance_seconds', 10))))
                updated = current.evaluate(now, startup, tolerance)
            fired = bool(action == 'poll' and updated != current and updated.state == 'fired')
            if updated != current:
                settings['current'] = asdict(updated) if updated else None
                atomic_write(self.path, config.data)
            return updated, fired, settings
