import datetime as dt

import pytest

import brain.read
from brain.entries import Entries
from brain.read import TooManyHits
from brain.write import Writer

from conftest import entry, event_files, lines_of


def test_an_invalid_line_and_a_torn_last_line_are_skipped(writer, reader, brain_dir):
    writer.write_entry(**entry(description="before"))
    [path] = event_files(brain_dir)
    with open(path, "ab") as file:
        file.write(b'not json\n{"id":"0199a8c4-no-envelope"}\n')
    writer.write_entry(**entry(description="after"))
    with open(path, "ab") as file:
        file.write(b'{"id":"0199a8c4-torn","description":"caf\xc3')  # cut mid-character

    assert [hit.description for hit in reader.search()] == ["before", "after"]


def test_search_returns_every_lean_hit_in_event_date_order(writer, other_machine, reader):
    writer.write_entry(**entry(event_date="2026-03-01", description="Tyres"))
    other_machine.write_entry(**entry(event_date="2026-01-01", description="Oil change"))
    writer.write_entry(**entry(event_date="2026-02-01", description="Brakes"))

    hits = reader.search()

    # Records from two files interleave by what they say happened, not where they sit.
    assert [hit.description for hit in hits] == ["Oil change", "Brakes", "Tyres"]
    assert [hit.description for hit in reader.search(newest_first=True)] == ["Tyres", "Brakes", "Oil change"]
    oil = hits[0]
    assert (oil.type, oil.event_date, oil.snippet) == ("journal", "2026-01-01", "## Service Oil and filter changed.")


def test_a_search_finding_more_than_the_ceiling_fails_with_ranges_that_fit(
    writer, reader, monkeypatch
):
    monkeypatch.setattr(brain.read, "CEILING", 3)
    for day, count in (("2026-01-01", 2), ("2026-01-02", 1), ("2026-01-03", 2), ("2026-01-04", 4)):
        for n in range(count):
            writer.write_entry(**entry(event_date=day, description=f"{day} {n}"))

    with pytest.raises(TooManyHits) as refused:
        reader.search("oil")

    assert refused.value.total == 9
    # Each range fits the ceiling, except a single day no date range can split.
    assert refused.value.ranges == [
        ("2026-01-01", "2026-01-02", 3), ("2026-01-03", "2026-01-03", 2), ("2026-01-04", "2026-01-04", 4),
    ]
    assert "9 entries match" in str(refused.value)
    assert "2026-01-01 to 2026-01-02 (3)" in str(refused.value)
    assert len(reader.search("oil", event_date_to="2026-01-02")) == 3


def test_a_pattern_matches_description_or_body_of_any_type_in_any_case(writer, reader):
    writer.write_entry(**entry(description="Started Zorblax", body="Two drops each morning."))
    writer.write_entry(**entry(
        type="snapshot", description="Current potions",
        body="## Current\n" + "Moonberry extract daily. " * 20 + "Zorblax two drops. " + "Glimmerol at night. " * 20,
    ))
    writer.write_entry(**entry(description="Oil change"))

    hits = reader.search("ZORBLAX OR fizzlorin")

    assert [(hit.type, hit.description) for hit in hits] == [
        ("journal", "Started Zorblax"), ("snapshot", "Current potions"),
    ]
    # A long body is cut to a stretch around its first match.
    assert hits[1].snippet.startswith("…") and "Zorblax two drops." in hits[1].snippet
    assert len(hits[1].snippet) < 200


def test_search_filters_by_type_event_date_recorded_time_and_details(brain_dir, tmp_path, reader):
    now = [dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)]
    writer = Writer(brain_dir, tmp_path / "data", clock=lambda: now[0])
    writer.write_entry(**entry(event_date="2026-01-10", description="January"))
    writer.write_entry(**entry(event_date="2026-02-10", description="February"))
    writer.write_entry(**entry(type="snapshot", description="Snapshot", details={"scope": "car"}))
    now[0] = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    writer.write_entry(**entry(event_date="2026-03-10", description="Late"))

    def found(**filters):
        return [hit.description for hit in reader.search(**filters)]

    assert found(types=["snapshot"]) == ["Snapshot"]
    assert found(event_date_from="2026-02-01", event_date_to="2026-03-10") == ["February", "Late"]
    assert found(recorded_after="2026-09-03") == ["Late"]
    assert found(details={"scope": "car"}) == ["Snapshot"]


def test_read_returns_full_records_for_a_list_of_ids_in_one_call(writer, reader):
    oil = writer.write_entry(**entry(event_date="2026-01-10", source="voice", details={"odometer": 48210}))
    tyres = writer.write_entry(**entry(event_date="2026-03-01", description="Tyres", body="Four new."))

    first, second = reader.read([tyres, "0199a8c4-missing", oil])

    assert first == {
        "id": oil, "entry": oil, "type": "journal", "version": 1, "recorded_at": first["recorded_at"],
        "event_date": "2026-01-10", "description": "Oil change", "source": "voice",
        "body": "## Service\nOil and filter changed.", "details": {"odometer": 48210}, "amendments": [],
    }
    assert (second["id"], second["source"], second["details"]) == (tyres, None, {})


def test_a_record_in_two_files_is_returned_once(writer, other_machine, reader, brain_dir):
    copied = writer.write_entry(**entry(description="Oil change"))
    other_machine.write_entry(**entry(description="Tyres", body="Four new tyres."))
    [line] = [line for path in event_files(brain_dir) for line in lines_of(path) if copied.encode() in line]
    [theirs] = [path for path in event_files(brain_dir) if line not in lines_of(path)]
    with open(theirs, "ab") as file:
        file.write(line + b"\n")

    assert [hit.id for hit in reader.search("oil")] == [copied]
    assert [record["id"] for record in reader.read([copied])] == [copied]


def test_search_finds_entries_by_the_pattern_or_the_entities_they_name(writer, entries, reader):
    entries.write_entity(slug="zorblax", name="Zorblax", kind="medication", body="A potion.")
    entries.write_journal(
        event_date="2026-01-01", description="Started Zorblax", body="Two drops.", entities=["zorblax"],
    )
    # Named, but never says the word: found only by its entity.
    # Written beneath the journal method, which would refuse the unrecorded dr-jekyll:
    # an entry from before that check, or a slug whose entity has not synced yet.
    writer.write_entry(**entry(
        event_date="2026-02-01", description="Doubled the dose", body="Four drops now.",
        details={"entities": ["zorblax", "dr-jekyll"]},
    ))
    # Says the word, but its entities were missed: found only by its text.
    entries.write_journal(event_date="2026-03-01", description="Zorblax refill", body="Collected.")
    writer.write_entry(**entry(event_date="2026-04-01", description="Oil change", body="Done.",
                               details={"entities": ["car"]}))

    def found(pattern=None, **filters):
        return [hit.description for hit in reader.search(pattern, **filters)]

    # The entity itself is a hit too, dated the day it was stated.
    assert found(entities=["zorblax"]) == ["Started Zorblax", "Doubled the dose", "Zorblax"]
    assert found("zorblax", entities=["zorblax"]) == [
        "Started Zorblax", "Doubled the dose", "Zorblax refill", "Zorblax",
    ]
    assert found(entities=["dr-jekyll", "car"]) == ["Doubled the dose", "Oil change"]
    assert found("zorblax", entities=["zorblax"], types=["journal"], event_date_to="2026-02-28") == [
        "Started Zorblax", "Doubled the dose",
    ]
    assert found(entities=[]) == []


def test_resolve_returns_the_likely_entities_for_each_name_and_no_others(entries, reader):
    entries.write_entity(
        slug="dr-jekyll", name="Dr. Jekyll", kind="person", aliases=["Dr. J"], body="The physician.",
    )
    entries.write_entity(slug="mr-hyde", name="Mr. Hyde", kind="person", body="Unrelated.")
    entries.write_entity(slug="zorblax", name="Zorblax", kind="medication", body="A potion.")
    entries.write_entity(slug="moonberry-extract", name="Moonberry extract", kind="supplement", body="Drops.")
    entries.write_entity(slug="mom", name="Mom", kind="person", body="My mother.")

    found = reader.resolve(["dr j", "Jekyll", "ZORBLAX", "zorblaxx", "moonberry", "Tom", "glimmerol"])

    def slugs(name):
        return [entity.slug for entity in found[name]]

    assert slugs("dr j") == ["dr-jekyll"]  # by alias, in any case and punctuation
    assert slugs("Jekyll") == ["dr-jekyll"]  # held whole as a word
    assert slugs("ZORBLAX") == slugs("zorblaxx") == ["zorblax"]  # spelled alike
    assert slugs("moonberry") == ["moonberry-extract"]
    assert slugs("Tom") == slugs("glimmerol") == []
    [jekyll] = found["dr j"]
    assert (jekyll.name, jekyll.kind, jekyll.aliases) == ("Dr. Jekyll", "person", ["Dr. J"])
    assert reader.resolve([]) == {}


def test_an_entity_restated_takes_the_newest_name_and_every_alias(brain_dir, data_dir, tmp_path, reader):
    # Two machines' ids order only by time, so each write takes a later millisecond.
    ticks = iter(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=n) for n in range(9))
    entries = Entries(Writer(brain_dir, data_dir, clock=lambda: next(ticks)), reader)
    other_machine = Writer(brain_dir, tmp_path / "other machine data", clock=lambda: next(ticks))
    entries.write_entity(slug="zorblax", name="Zorblax", kind="potion", aliases=["ZB"], body="A potion.")
    # Another machine adds an alias of its own before the two sync.
    Entries(other_machine, reader).write_entity(
        slug="zorblax", name="Zorblax", kind="potion", aliases=["the green drops"], body="A potion.",
    )
    newest = entries.write_entity(
        slug="zorblax", name="Zorblax tincture", kind="medication", aliases=["the blue drops"], body="Blue.",
    )

    [entity] = reader.resolve(["the green drops"])["the green drops"]
    assert (entity.id, entity.name, entity.kind) == (newest, "Zorblax tincture", "medication")
    assert entity.aliases == ["ZB", "the blue drops", "the green drops"]
    assert reader.known_slugs(["zorblax", "glimmerol"]) == {"zorblax"}


def test_resolve_keeps_to_its_limit_best_first(entries, reader):
    for slug in ("dr-jekyll", "dr-jekyll-senior", "dr-lanyon", "dr-who"):
        entries.write_entity(slug=slug, name=slug.replace("-", " "), kind="person", body="A doctor.")

    assert [e.slug for e in reader.resolve(["dr jekyll"], limit=2)["dr jekyll"]] == [
        "dr-jekyll", "dr-jekyll-senior",
    ]
