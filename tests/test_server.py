import asyncio
import json
import os
import subprocess
import sys

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

from conftest import PLUGIN
from server.serve import build

TOOLS = {"write", "search", "read"}


@pytest.fixture
def server(brain_dir, data_dir):
    brain_dir.mkdir()
    return build(brain_dir, data_dir)


def calls(server, *steps):
    """Runs each (tool, arguments) in turn, in one session, and returns each
    result: the parsed JSON, the text of a tool that returns text, or the error
    text of an error result."""

    async def run():
        results = []
        async with Client(server) as client:
            for name, arguments in steps:
                result = await client.call_tool(name, arguments)
                text = result.content[0].text
                results.append(("error", text) if result.is_error else json.loads(text) if name != "read" else text)
        return results

    return asyncio.run(run())


def journal(slug: str, **fields) -> tuple[str, dict]:
    return ("write", {"type": "journal", "version": 1, "slug": slug, "event_date": "2026-09-14",
                      "description": "Oil change", "body": "Oil changed.", **fields})


def entity(slug: str, **fields) -> tuple[str, dict]:
    return ("write", {"type": "entity", "version": 1, "slug": slug, "event_date": "2026-09-01",
                      "description": slug.title(), "body": "Recorded.", **fields})


def test_every_tool_is_listed_with_its_rules(server):
    async def run():
        async with Client(server) as client:
            return (await client.list_tools()).tools

    tools = {tool.name: tool for tool in asyncio.run(run())}
    assert set(tools) == TOOLS
    assert "merges" in tools["write"].description
    assert tools["search"].annotations.read_only_hint is True
    assert tools["write"].annotations.read_only_hint is False
    assert tools["read"].annotations.read_only_hint is True


def test_an_entry_linking_to_an_entity_is_written_found_and_read(server):
    zorblax, written, named, found, read = calls(
        server,
        entity("zorblax", description="Zorblax", aliases=["the car"], details={"kind": "vehicle"}),
        journal("2026-09-14-oil-change", description="Oil change at 48k", links=["zorblax"]),
        ("search", {"names": ["the car"], "types": ["entity"]}),
        ("search", {"slugs": ["zorblax"], "types": ["journal"]}),
        ("read", {"ids": []}),
    )

    assert [(hit["slugs"], hit["names"]) for hit in named["hits"]] == [(["zorblax"], ["the car"])]
    assert [hit["id"] for hit in found["hits"]] == [written["id"]]
    assert found["hits"][0]["description"] == "Oil change at 48k"
    assert read == "No record has any of those ids."
    assert zorblax["id"] != written["id"]


def test_a_revision_is_read_back_with_its_amendment(server):
    [written] = calls(server, journal("oil-change"))
    revision, read = calls(
        server,
        ("write", {"type": "journal", "version": 1, "entry": written["id"],
                   "description": "Oil change and tyre rotation", "body": "The tyres were rotated too."}),
        ("read", {"ids": [written["id"]]}),
    )

    assert read.splitlines()[0] == "# Oil change and tyre rotation"
    assert f"id: {written['id']} | type: journal | event_date: 2026-09-14" in read.splitlines()[1]
    body, amendments = read.split("\n\n## Amendments\n\n### ")
    assert body.endswith("\n\nOil changed.")
    assert amendments.splitlines()[1:] == ["The tyres were rotated too."]
    assert revision["id"] != written["id"]


def test_a_read_comes_back_as_markdown_with_the_body_on_real_lines(server):
    zorblax, written = calls(
        server,
        entity("zorblax", description="Zorblax", aliases=["the hover car"], details={"kind": "vehicle"}),
        journal("oil-change-at-48k", description="Oil change at 48k", body="## Service\nOil and filter changed.\n\nBrakes worn.",
                links=["zorblax"], details={"odometer": 48210}, source="voice"),
    )
    [read] = calls(server, ("read", {"ids": [zorblax["id"], written["id"]]}))

    # In event-date order: the entity's 2026-09-01 comes before the entry's 2026-09-14.
    car, oil_change = read.split("\n\n---\n\n")
    assert car.splitlines()[0] == "# Zorblax"
    assert {"slugs: zorblax", "aliases: the hover car", "kind: vehicle"} <= set(car.splitlines())
    assert oil_change.splitlines()[:5] == [
        "# Oil change at 48k",
        oil_change.splitlines()[1],
        "slugs: oil-change-at-48k",
        "links: zorblax",
        "odometer: 48210",
    ]
    assert "source: voice" in oil_change.splitlines()[1]
    assert oil_change.endswith("## Service\nOil and filter changed.\n\nBrakes worn.")


def test_a_failure_the_model_can_fix_is_an_error_result_with_how(server):
    first, taken, unknown, names, pattern, date = calls(
        server,
        journal("oil-change"),
        journal("oil-change"),
        journal("tyres", links=["nobody"]),
        ("search", {"names": ["nobody"]}),
        ("search", {"pattern": "-oil"}),
        ("search", {"event_date_from": "September"}),
    )

    assert taken[0] == "error" and first["id"] in taken[1] and "revise that entry" in taken[1]
    assert unknown[0] == "error" and "nobody" in unknown[1] and "create its entry first" in unknown[1]
    assert names[0] == "error" and "needs types" in names[1]
    assert pattern[0] == "error" and "a word to find" in pattern[1]
    assert date[0] == "error" and "YYYY-MM-DD" in date[1]


def test_a_search_past_the_ceiling_fails_with_ranges_to_search(server):
    steps = [journal(f"walk-{month}-{n}", event_date=f"2026-{month:02}-01", description=f"Walk {n}", body="A walk.")
             for month in range(1, 13) for n in range(10)]
    *_, too_many = calls(server, *steps, ("search", {"pattern": "walk"}))

    assert too_many[0] == "error"
    assert "120 entries match" in too_many[1] and "2026-01-01 to" in too_many[1]


def test_an_entry_of_a_type_the_server_knows_nothing_of_is_written_found_revised_and_read(server):
    filed = {"path": "car/invoice.pdf", "sha256": "a" * 64}
    document, captured, found, linked = calls(
        server,
        ("write", {"type": "document", "version": 1, "slug": "oil-change-invoice", "event_date": "2026-09-14",
                   "description": "Oil change invoice", "body": "Oil and filter, 48k.", "details": filed}),
        journal("filed-the-invoice", description="Filed the oil change invoice", links=["oil-change-invoice"]),
        ("search", {"types": ["document"], "details": {"sha256": filed["sha256"]}}),
        ("search", {"slugs": ["oil-change-invoice"]}),
    )
    revised, read = calls(
        server,
        ("write", {"type": "document", "version": 1, "entry": document["id"], "details": {"sha256": "b" * 64},
                   "body": "The garage sent a corrected invoice."}),
        ("read", {"ids": [document["id"]]}),
    )

    assert [hit["id"] for hit in found["hits"]] == [document["id"]]
    assert {hit["id"] for hit in linked["hits"]} == {document["id"], captured["id"]}
    assert f"sha256: {'b' * 64}" in read.splitlines() and "path: car/invoice.pdf" in read.splitlines()
    assert revised["id"] != document["id"]


def test_the_server_answers_over_stdio_and_keeps_stdout_for_the_protocol(brain_dir, data_dir):
    brain_dir.mkdir()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "server.serve"],
        env={"PYTHONPATH": str(PLUGIN), "BRAIN_DIR": str(brain_dir), "BRAIN_DATA_DIR": str(data_dir)},
    )

    async def run():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            name, arguments = journal("oil-change")
            written = await session.call_tool(name, arguments)
            found = await session.call_tool("search", {"pattern": "oil"})
            return json.loads(written.content[0].text), json.loads(found.content[0].text)

    written, found = asyncio.run(run())
    assert [hit["id"] for hit in found["hits"]] == [written["id"]]


def test_a_server_with_no_brain_folder_exits_saying_so(tmp_path):
    env = os.environ | {"PYTHONPATH": str(PLUGIN), "BRAIN_DIR": "${user_config.brain_folder}",
                        "BRAIN_DATA_DIR": str(tmp_path / "data")}

    done = subprocess.run([sys.executable, "-m", "server.serve"], env=env, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60)

    assert done.returncode == 1
    assert done.stdout == ""
    assert "BRAIN_DIR is not set" in done.stderr
