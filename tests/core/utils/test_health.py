"""Tests for encodapy.utils.health module."""

from datetime import datetime, timedelta

import pytest

from encodapy.utils.health import update_health_file


@pytest.mark.asyncio
async def test_update_health_file_without_previous_timestamp_writes_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a previous health timestamp a health file with status OK is created."""

    monkeypatch.chdir(tmp_path)
    timestamp_now = datetime(2026, 1, 1, 12, 0, 0)

    await update_health_file(
        time_cycle=5, timestamp_health=None, timestamp_now=timestamp_now
    )

    health_file = tmp_path / "health"
    assert health_file.exists()
    assert health_file.read_text(encoding="utf-8") == "OK"


@pytest.mark.asyncio
async def test_update_health_file_with_recent_timestamp_writes_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A health timestamp within the cycle duration writes the health file."""

    monkeypatch.chdir(tmp_path)
    timestamp_now = datetime(2026, 1, 1, 12, 0, 0)
    timestamp_health = timestamp_now - timedelta(minutes=2)

    await update_health_file(
        time_cycle=5, timestamp_health=timestamp_health, timestamp_now=timestamp_now
    )

    health_file = tmp_path / "health"
    assert health_file.exists()
    assert health_file.read_text(encoding="utf-8") == "OK"


@pytest.mark.asyncio
async def test_update_health_file_with_outdated_timestamp_writes_no_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A health timestamp older than the cycle duration writes no health file."""

    monkeypatch.chdir(tmp_path)
    timestamp_now = datetime(2026, 1, 1, 12, 0, 0)
    timestamp_health = timestamp_now - timedelta(minutes=10)

    await update_health_file(
        time_cycle=5, timestamp_health=timestamp_health, timestamp_now=timestamp_now
    )

    assert not (tmp_path / "health").exists()
