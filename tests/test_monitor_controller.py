from __future__ import annotations

from monitor_controller import HistoryBuffer, history_capacity


def test_history_capacity_default_is_60() -> None:
    assert history_capacity(update_interval_seconds=5, history_minutes=5) == 60


def test_history_capacity_uses_interval_and_minutes() -> None:
    assert history_capacity(update_interval_seconds=10, history_minutes=2) == 12


def test_history_capacity_never_drops_below_one() -> None:
    assert history_capacity(update_interval_seconds=0, history_minutes=5) == 1
    assert history_capacity(update_interval_seconds=5, history_minutes=0) == 1


def test_history_buffer_drops_oldest_values() -> None:
    buffer = HistoryBuffer(capacity=3)

    buffer.append(1)
    buffer.append(2)
    buffer.append(None)
    buffer.append(3)
    buffer.append(4)

    assert buffer.as_list() == [2.0, 3.0, 4.0]
