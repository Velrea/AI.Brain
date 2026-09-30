import datetime as dt
import json
import uuid

import pytest

from brain import format
from brain.format import RecordError, check, encode, file_created_at, is_event_file, new_file_name

from conftest import entry


def test_a_new_file_is_named_for_the_time_it_is_started():
    at = dt.datetime(2026, 9, 28, 23, 14, 32, 123000, dt.timezone.utc)
    name = new_file_name(at)
    assert is_event_file(name)
    assert name.startswith("h-") and name.endswith(".jsonl")
    assert file_created_at(name) == at


@pytest.mark.parametrize(
    "name",
    ["events.jsonl", "c-0199a8c4-0000-7000-8000-000000000000.jsonl", "h-not-a-uuid.jsonl"],
)
def test_other_names_are_not_event_files(name):
    assert not is_event_file(name)


def test_uuid7_carries_version_variant_and_time():
    at = dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc)
    value = format.uuid7(at)
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
    assert format.uuid7_time(value) == at
    assert format.uuid7(at) != value


@pytest.mark.parametrize("missing", ["type", "version", "event_date", "description", "body"])
def test_a_record_missing_a_required_field_is_rejected(missing):
    fields = entry()
    del fields[missing]
    with pytest.raises(RecordError, match=missing):
        check(fields)


@pytest.mark.parametrize("stamped", ["id", "recorded_at"])
def test_a_record_setting_a_stamped_field_is_rejected(stamped):
    with pytest.raises(RecordError, match=stamped):
        check(entry(**{stamped: "anything"}))


def test_a_type_may_carry_fields_of_its_own():
    fields = entry(type="vehicle_service", odometer=48210, parts=["oil", "filter"])
    assert check(fields) == fields


@pytest.mark.parametrize("value", [{1, 2}, float("nan"), object()])
def test_a_field_that_is_not_json_is_rejected(value):
    with pytest.raises(RecordError, match="odometer"):
        check(entry(odometer=value))


def test_a_line_holds_the_common_fields_first_then_the_types_own():
    record = {"odometer": 1, "body": "b", "id": "x", "type": "t", "recorded_at": "r"}
    assert list(json.loads(encode(record))) == ["id", "type", "recorded_at", "body", "odometer"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"type": ""},
        {"type": 3},
        {"version": 0},
        {"version": "1"},
        {"version": True},
        {"event_date": "2026-02-30"},
        {"event_date": "14 September 2026"},
        {"event_date": "2026-09-14T10:00:00"},
        {"description": "two\nlines"},
        {"description": "   "},
        {"body": None},
        {"body": "  \n"},
        {"source": ""},
        {"source": None},
    ],
)
def test_a_value_of_the_wrong_kind_is_rejected(overrides):
    with pytest.raises(RecordError):
        check(entry(**overrides))


def test_source_is_optional_and_body_may_hold_many_lines():
    check(entry(body="line one\nline two\n"))
    check(entry(source="email"))


def test_a_record_encodes_as_one_line_of_utf8_json():
    record = {"id": "x", "body": "café\nnext\u2028line"}
    line = encode(record)
    assert line.endswith(b"\n") and line.count(b"\n") == 1
    text = line.decode("utf-8")
    assert "café" in text and "\u2028" not in text
    assert json.loads(text) == record


def test_text_that_is_not_valid_unicode_is_rejected():
    with pytest.raises(RecordError):
        encode({"body": "\ud800"})
