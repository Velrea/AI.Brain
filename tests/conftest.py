import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from brain.read import Reader
from brain.write import Writer

PLUGIN = Path(__file__).resolve().parent.parent / "plugin"

_numbers = itertools.count()


def entry(**overrides) -> dict:
    """Arguments for Writer.write, under a slug of its own."""
    fields = {
        "type": "journal",
        "version": 1,
        "event_date": "2026-09-14",
        "description": "Oil change",
        "body": "## Service\nOil and filter changed.",
        "slug": f"entry-{next(_numbers)}",
    }
    return fields | overrides


def create(writer: Writer, slug: str, **fields) -> str:
    """Creates an entry through Writer.write, a journal entry unless told otherwise."""
    return writer.write(**{
        "type": "journal", "version": 1, "slug": slug, "event_date": "2026-01-01", "description": slug,
        "body": "Recorded.", **fields,
    })


def unchecked(writer: Writer, **overrides) -> str:
    """Appends a record beneath Writer.write's checks, as a machine that had not
    yet synced the entries it would be checked against might have written it."""
    fields = entry(**overrides)
    slug = fields.pop("slug")
    return writer._append(**{"slugs": [slug], **fields})


def event_files(brain_dir: Path) -> list[Path]:
    return sorted((brain_dir / "events").glob("*.jsonl"))


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
def brain_dir(tmp_path: Path) -> Path:
    return tmp_path / "brain"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "machine data"


@pytest.fixture
def writer(brain_dir: Path, data_dir: Path) -> Writer:
    return Writer(brain_dir, data_dir)


@pytest.fixture
def other_machine(brain_dir: Path, tmp_path: Path) -> Writer:
    """A second machine writing to the same Brain, so to a file of its own."""
    return Writer(brain_dir, tmp_path / "other machine data")


@pytest.fixture
def reader(brain_dir: Path, data_dir: Path) -> Reader:
    return Reader(brain_dir, data_dir)