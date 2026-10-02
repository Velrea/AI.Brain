import datetime as dt

import pytest

from brain.entries import UnknownEntities
from brain.format import RecordError

from conftest import event_files, records_of


def test_a_journal_is_written_as_a_version_1_journal_with_no_details(entries, brain_dir):
    entry_id = entries.write_journal(
        event_date="2026-09-14", description="Oil change", body="Oil and filter changed."
    )

    [path] = event_files(brain_dir)
    [record] = records_of(path)
    assert record["id"] == entry_id
    assert (record["type"], record["version"], record["details"]) == ("journal", 1, {})


def test_a_snapshot_is_written_on_the_day_taken_with_its_scope(entries, brain_dir):
    entry_id = entries.write_snapshot(
        scope="current potions", description="Current potions", body="Zorblax, two drops."
    )
    with pytest.raises(RecordError):
        entries.write_snapshot(scope=" ", description="Blank scope", body="Nothing.")

    [path] = event_files(brain_dir)
    [record] = records_of(path)
    assert record["id"] == entry_id
    assert (record["type"], record["version"]) == ("snapshot", 1)
    assert record["event_date"] == dt.date.today().isoformat()
    assert record["details"] == {"scope": "current potions"}


def test_a_journal_names_its_entities_once_each_by_slug(entries, brain_dir):
    for slug in ("zorblax", "dr-jekyll"):
        entries.write_entity(slug=slug, name=slug, kind="thing", body="Recorded.")
    entries.write_journal(
        event_date="2026-09-14", description="Doubled the Zorblax", body="Dr. J doubled it.",
        entities=["zorblax", "dr-jekyll", "zorblax"],
    )
    for bad in (["Dr. Jekyll"], "zorblax", [""]):
        with pytest.raises(RecordError):
            entries.write_journal(event_date="2026-09-14", description="Bad", body="Bad.", entities=bad)

    [path] = event_files(brain_dir)
    *_, record = records_of(path)
    assert record["details"] == {"entities": ["zorblax", "dr-jekyll"]}


def test_a_journal_naming_an_unrecorded_entity_is_refused(entries, brain_dir):
    entries.write_entity(slug="zorblax", name="Zorblax", kind="medication", body="A potion.")

    with pytest.raises(UnknownEntities) as refused:
        entries.write_journal(
            event_date="2026-09-14", description="Doubled it", body="Dr. J doubled it.",
            entities=["zorblax", "dr-jekyll", "mr-hyde"],
        )

    assert refused.value.slugs == ["dr-jekyll", "mr-hyde"]
    [path] = event_files(brain_dir)
    assert [record["type"] for record in records_of(path)] == ["entity"]  # nothing written


def test_an_entity_is_written_through_its_own_method(entries, brain_dir):
    entity_id = entries.write_entity(
        slug="dr-jekyll", name="Dr. Jekyll", kind="person", aliases=["Dr. J", "Henry"],
        body="The family physician.",
    )
    for bad in ({"slug": "Dr Jekyll"}, {"kind": " "}, {"aliases": "Dr. J"}, {"aliases": ["two\nlines"]}):
        with pytest.raises(RecordError):
            entries.write_entity(**{
                "slug": "dr-jekyll", "name": "Dr. Jekyll", "kind": "person", "body": "Bad.", **bad,
            })

    [path] = event_files(brain_dir)
    [record] = records_of(path)
    assert record["id"] == entity_id
    assert (record["type"], record["version"], record["description"]) == ("entity", 1, "Dr. Jekyll")
    assert record["event_date"] == dt.date.today().isoformat()
    assert record["details"] == {"slug": "dr-jekyll", "kind": "person", "aliases": ["Dr. J", "Henry"]}
