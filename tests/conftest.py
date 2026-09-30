import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from brain.write import Writer

PLUGIN = Path(__file__).resolve().parent.parent / "plugin"


def entry(**overrides) -> dict:
    fields = {
        "type": "journal",
        "version": 1,
        "event_date": "2026-09-14",
        "description": "Oil change",
        "body": "## Service\nOil and filter changed.",
    }
    return fields | overrides


def event_files(event_store: Path) -> list[Path]:
    return sorted((event_store / "events").glob("*.jsonl"))


def lines_of(path: Path) -> list[bytes]:
    data = path.read_bytes()
    assert data.endswith(b"\n")
    return data.split(b"\n")[:-1]


def records_of(path: Path) -> list[dict]:
    return [json.loads(line) for line in lines_of(path)]


def python(code: str, *args: str) -> subprocess.Popen:
    """Starts a separate Python process that can import the package."""
    env = os.environ | {"PYTHONPATH": str(PLUGIN)}
    return subprocess.Popen(
        [sys.executable, "-c", code, *args],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "event store"


@pytest.fixture
def state(tmp_path: Path) -> Path:
    return tmp_path / "machine state"


@pytest.fixture
def writer(store: Path, state: Path) -> Writer:
    return Writer(store, state)
