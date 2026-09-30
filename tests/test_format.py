import datetime as dt
import json

import pytest

from brain.format import RecordError, check_entry, encode, file_created_at, is_event_file, new_file_name

from conftest import entry


def test_a_new_file_is_named_for_the_time_it_is_started():
    at = dt.datetime(2026, 9, 28, 23, 14, 32, 123000, dt.timezone.utc)
    name = new_file_name(at)
    assert is_event_file(name)
    assert file_created_at(name) == at


@pytest.mark.parametrize(
    "overrides",
    [
        {"type": ""},
        {"description": "   "},
        {"description": "two\nlines"},
        {"body": "  \n"},
        {"event_date": "2026-02-30"},
        {"event_date": "14 September 2026"},
        {"source": ""},
        {"details": ["not", "an", "object"]},
        {"details": {"parts": {"oil", "filter"}}},
        {"details": {"amount": float("nan")}},
    ],
)
def test_a_blank_or_invalid_field_is_rejected(overrides):
    fields = {"source": None, "details": {}} | entry(**overrides)
    with pytest.raises(RecordError):
        check_entry(**fields)


def test_a_record_is_one_line_whatever_its_text_holds():
    record = {"id": "x", "body": "café\nnext\u2028line\u2029end", "details": {"note": "a\nb"}}
    line = encode(record)
    assert line.endswith(b"\n") and line.count(b"\n") == 1
    text = line.decode("utf-8")
    assert "\u2028" not in text and "\u2029" not in text
    assert json.loads(text) == record
