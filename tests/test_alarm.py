from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from dataclasses import asdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import yaml

from alarm_model import Alarm, UTC, parse_time, resolve_local
from alarm_store import AlarmStore
from app_config import AppConfig

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)


def prepare(path):
    AppConfig.load(path)
    alarm = Alarm.create(NOW + timedelta(minutes=1), 'Europe/Berlin', 'Tea', NOW)
    AlarmStore(path).transact('set', asdict(alarm), now=NOW)
    return alarm


@pytest.mark.parametrize('text', ['14:30', '1430'])
def test_time_formats(text):
    assert parse_time(text) == (14, 30)


@pytest.mark.parametrize('text', ['25:00', '12:60', 'abc', '123'])
def test_invalid_time(text):
    with pytest.raises(ValueError):
        parse_time(text)


def test_dst_gap_and_fold():
    zone = ZoneInfo('Europe/Berlin')
    assert resolve_local(datetime(2026, 3, 29, 2, 30), zone) == []
    choices = resolve_local(datetime(2026, 10, 25, 2, 30), zone)
    assert len(choices) == 2
    assert (choices[1] - choices[0]).total_seconds() == 3600


def test_restart_and_once_only(tmp_path):
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    assert AlarmStore(path).transact(startup=True, now=NOW)[0] == alarm
    current, fired, _ = AlarmStore(path).transact(now=alarm.due)
    assert fired and current.state == 'fired'
    for moment in [alarm.due, NOW, alarm.due + timedelta(days=1)]:
        current, fired, _ = AlarmStore(path).transact(startup=True, now=moment)
        assert not fired and current.state == 'fired'


@pytest.mark.parametrize('startup,late,state', [(True, 1, 'missed'), (False, 10, 'fired'), (False, 11, 'missed')])
def test_missed_policy(tmp_path, startup, late, state):
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    current, fired, _ = AlarmStore(path).transact(startup=startup, now=alarm.due + timedelta(seconds=late))
    assert current.state == state
    assert fired == (state == 'fired')


def test_stale_geometry_and_unrelated_edits_preserved(tmp_path):
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    stale = AppConfig.load(path)
    fresh = AppConfig.load(path)
    fresh.data['metrics']['cpu']['label'] = 'Processor'
    fresh.save()
    AlarmStore(path).transact(now=alarm.due)
    params = stale.clock_params()
    params['x'] = 123
    stale.update_clock_params(params)
    loaded = AppConfig.load(path)
    assert loaded.get('alarm.current')['state'] == 'fired'
    assert loaded.get('metrics.cpu.label') == 'Processor'
    assert loaded.get('clock.geometry.x') == 123


def test_cancel_and_replacement_guard(tmp_path):
    path = tmp_path / 'config.yaml'
    old = prepare(path)
    new = Alarm.create(NOW + timedelta(minutes=2), 'UTC', 'New', NOW)
    AlarmStore(path).transact('set', asdict(new), now=NOW)
    assert AlarmStore(path).transact('cancel', old.id, now=NOW)[0].state == 'armed'
    assert AlarmStore(path).transact('cancel', new.id, now=NOW)[0].state == 'cancelled'
    assert not AlarmStore(path).transact(now=new.due)[1]


def test_failed_claim_keeps_record_armed(tmp_path, monkeypatch):
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr('alarm_store.atomic_write', fail)
    with pytest.raises(OSError):
        AlarmStore(path).transact(now=alarm.due)
    assert AppConfig.load(path).get('alarm.current')['state'] == 'armed'


def claim(path, when):
    try:
        return AlarmStore(path).transact(now=when)[1]
    except BlockingIOError:
        return False


def test_competing_processes_claim_at_most_once(tmp_path):
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    with ProcessPoolExecutor(max_workers=2, mp_context=get_context('spawn')) as pool:
        results = list(pool.map(claim, [path] * 8, [alarm.due] * 8))
    assert sum(results) == 1
    assert AppConfig.load(path).get('alarm.current')['state'] == 'fired'


def test_invalid_record_is_not_rearmed(tmp_path):
    path = tmp_path / 'config.yaml'
    AppConfig.load(path)
    data = yaml.safe_load(path.read_text())
    data['alarm']['current'] = {'state': 'armed'}
    path.write_text(yaml.safe_dump(data))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='Invalid alarm record'):
        AlarmStore(path).transact(now=NOW)
    assert path.read_bytes() == before


def test_atomic_failure_preserves_original(tmp_path, monkeypatch):
    from config_storage import atomic_write
    path = tmp_path / 'config.yaml'
    prepare(path)
    before = path.read_bytes()
    def fail(*args):
        raise OSError('replace failed')
    monkeypatch.setattr('config_storage.os.replace', fail)
    with pytest.raises(OSError):
        atomic_write(path, {})
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('.config.yaml.*'))


def test_lock_contention_does_not_consume_alarm(tmp_path):
    from config_storage import config_lock
    path = tmp_path / 'config.yaml'
    alarm = prepare(path)
    with config_lock(path):
        with pytest.raises(BlockingIOError):
            AlarmStore(path).transact(now=alarm.due)
    assert AlarmStore(path).transact(now=alarm.due)[1]


def test_explicit_reset_to_defaults_clears_alarm(tmp_path):
    from app_config import DEFAULT_CONFIG
    from config_storage import atomic_write, config_lock
    path = tmp_path / 'config.yaml'
    prepare(path)
    with config_lock(path):
        atomic_write(path, DEFAULT_CONFIG)
    assert AlarmStore(path).transact(now=NOW)[0] is None
