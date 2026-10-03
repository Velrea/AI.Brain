import pytest

from brain.write import SlugTaken, UnknownLinks
from brain.format import RecordError

from conftest import create, event_files, records_of


def written(brain_dir) -> list[dict]:
    return [record for path in event_files(brain_dir) for record in records_of(path)]


def test_an_entry_of_any_type_is_created_under_its_slug(writer, brain_dir):
    create(writer, "zorblax", type="entity")
    entry_id = writer.write(
        type="task", version=2, slug="renew-the-permit", event_date="2026-09-14", description="Renew the permit",
        body="Due in May.", links=["zorblax", "zorblax"], aliases=["permit", "permit"], details={"due": "2027-05-01"},
        source="voice",
    )

    *_, record = written(brain_dir)
    assert record["id"] == record["entry"] == entry_id
    assert (record["type"], record["version"], record["source"]) == ("task", 2, "voice")
    assert (record["slugs"], record["aliases"], record["links"], record["revises"]) == (
        ["renew-the-permit"], ["permit"], ["zorblax"], [],
    )
    assert record["details"] == {"due": "2027-05-01"}


def test_a_slug_already_carried_is_refused_naming_the_entry(writer, brain_dir):
    held = create(writer, "zorblax", type="entity", description="Zorblax")

    with pytest.raises(SlugTaken) as refused:
        create(writer, "zorblax", description="Another Zorblax")

    assert held in str(refused.value) and "Zorblax" in str(refused.value)
    assert len(written(brain_dir)) == 1


def test_a_link_no_entry_carries_is_refused_and_nothing_is_written(writer, brain_dir):
    create(writer, "zorblax", type="entity")

    with pytest.raises(UnknownLinks) as refused:
        create(writer, "doubled-it", links=["zorblax", "dr-jekyll", "mr-hyde"])

    assert refused.value.slugs == ["dr-jekyll", "mr-hyde"]
    assert [record["type"] for record in written(brain_dir)] == ["entity"]


@pytest.mark.parametrize("fields", [
    {"slug": None}, {"slug": "Dr Jekyll"}, {"type": "Journal"}, {"links": "zorblax"}, {"links": ["Zorblax"]},
    {"aliases": "Dr. J"}, {"aliases": ["two\nlines"]}, {"details": ["not", "fields"]}, {"body": " "},
])
def test_a_badly_formed_entry_is_refused(writer, brain_dir, fields):
    with pytest.raises(RecordError):
        create(writer, **{"slug": "an-entry", **fields})
    assert event_files(brain_dir) == []


def test_a_revision_replaces_fields_adds_names_and_keeps_its_amendment(writer, reader, brain_dir):
    create(writer, "zorblax", type="entity")
    original = create(writer, "started-zorblax", details={"dose": 2, "form": "drops"})
    revision = writer.write(
        type="journal", version=1, entry=original, description="Started Zorblax tincture",
        event_date="2026-01-03", links=["zorblax"], slug="zorblax-start", aliases=["the start"],
        details={"dose": 3, "form": None}, body="Correction: it was three drops.",
    )

    [record] = reader.read([original])
    assert (record["description"], record["event_date"], record["links"]) == (
        "Started Zorblax tincture", "2026-01-03", ["zorblax"],
    )
    assert (record["slugs"], record["aliases"], record["details"]) == (
        ["started-zorblax", "zorblax-start"], ["the start"], {"dose": 3},
    )
    assert record["body"] == "Recorded."
    assert [(a["id"], a["body"]) for a in record["amendments"]] == [(revision, "Correction: it was three drops.")]
    *_, on_disk = written(brain_dir)
    assert on_disk["entry"] == original
    assert on_disk["revises"] == ["description", "event_date", "links"]
    assert on_disk["details"] == {"dose": 3, "form": None}


def test_a_revision_that_changes_nothing_or_names_no_entry_of_its_type_is_refused(writer, brain_dir):
    original = create(writer, "started-zorblax")
    snapshot = create(writer, "potions", type="snapshot")
    before = len(written(brain_dir))

    with pytest.raises(RecordError, match="must change"):
        writer.write(type="journal", version=1, entry=original)
    with pytest.raises(RecordError, match="non-empty"):
        writer.write(type="journal", version=1, entry=original, body=" ")
    with pytest.raises(RecordError, match="is a snapshot, not a journal"):
        writer.write(type="journal", version=1, entry=snapshot, description="Not a journal")
    with pytest.raises(RecordError, match="no entry"):
        writer.write(type="journal", version=1, entry="0199a8c4-0000-7000-8000-000000000000", description="Gone")
    with pytest.raises(UnknownLinks):
        writer.write(type="journal", version=1, entry=original, links=["glimmerol"])
    assert len(written(brain_dir)) == before
