"""The Brain's MCP server, over stdio: the core module's write, search, and
read, each as a tool.

It is the translation between the core module and the model's context, and
holds no logic about the data: every tool calls the core module, and each
tool's description carries the rules the call enforces. No tool is for a
particular type: what a type means is the skill's that writes it. A failure
the model can act on, such as a slug already taken or a search that finds too
much, comes back as an error result with how to put it right.
"""

import functools
import json
import logging
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from brain.entries import Entries
from brain.format import RecordError
from brain.lock import LockTimeout
from brain.read import Reader
from brain.write import AppendBlocked, Writer
from server.folders import FolderError, brain_dir, data_dir

log = logging.getLogger("brain")

INSTRUCTIONS = """\
The Brain is the user's journal of whatever they choose to record: an append-only \
log of entries, each of a type its skill defines, named by slugs and linked to other \
entries by slug. Nothing is ever edited; a correction is a \
revision through `write`. Find with `search`, then `read` only the ids you pick. \
Search by names for the slugs of what you mean before linking to or searching by them."""

READS = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
WRITES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

# Failures the model can put right, or retry: each comes back as an error result.
_ANTICIPATED = (RecordError, ValueError, LockTimeout, AppendBlocked)


def _tool(fn: Callable[..., Any]) -> Callable[..., str]:
    """Returns the call's result as compact JSON, or as it is when it is already
    text, and an anticipated failure as an error result with its message."""

    @functools.wraps(fn)
    def call(*args, **kwargs) -> str:
        try:
            result = fn(*args, **kwargs)
        except _ANTICIPATED as error:
            raise ToolError(str(error)) from error
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, separators=(",", ":"))

    return call


def render(records: list[dict]) -> str:
    """Records as Markdown for the model: each a heading and its fields, then its
    body on real lines. JSON would put a whole body on one escaped line, which a
    model cannot page through when a host saves a large result to a file."""
    if not records:
        return "No record has any of those ids."
    return "\n\n---\n\n".join(_render(record) for record in records)


def _render(record: dict) -> str:
    fields = [f"{name}: {record[name]}" for name in ("id", "type", "event_date", "recorded_at", "source") if record.get(name)]
    lines = [f"# {record['description']}", " | ".join(fields)]
    for name in ("slugs", "aliases", "links"):
        if record[name]:
            lines.append(f"{name}: " + ", ".join(record[name]))
    if record["merged_into"]:
        lines.append(f"merged into: {record['merged_into']}")
    for name, value in record["details"].items():
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            value = ", ".join(value)
        elif not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"{name}: {value}")
    text = "\n".join(lines) + "\n\n" + record["body"].strip()
    if record.get("amendments"):
        text += "\n\n## Amendments"
        for amendment in record["amendments"]:
            text += f"\n\n### {amendment['recorded_at']}\n{amendment['body'].strip()}"
    return text


def build(brain: Path, data: Path) -> MCPServer:
    """The server for one Brain folder, keeping this machine's files in `data`."""
    reader = Reader(brain, data)
    entries = Entries(Writer(brain, data), reader)
    server = MCPServer("brain", instructions=INSTRUCTIONS)

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def write(
        type: str,
        version: int,
        entry: str | None = None,
        slug: str | None = None,
        event_date: str | None = None,
        description: str | None = None,
        body: str | None = None,
        links: list[str] | None = None,
        aliases: list[str] | None = None,
        details: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> dict:
        """Creates an entry of any type, or revises one, and returns the record's {"id": ...}.

        type: the kind of entry, a slug. version: the version of that type's shape, from 1.
        To create, leave out entry and give slug, event_date, description, and body:
          slug: the entry's name, lowercase letters and digits in words joined by
            hyphens, carried by no other entry. A slug already recorded is refused,
            naming the entry that carries it.
          event_date: when it happened, a local date, YYYY-MM-DD.
          description: one line. body: Markdown, the entry itself.
        To revise, give entry, the id of an entry of the same type, and what changes:
          description, event_date, links: each given replaces the entry's.
          details: each field replaces the entry's field of that name; null removes it.
          slug, aliases: add to the entry's names. A slug another entry was created
            under merges that entry into this one.
          body: an amendment, kept under the entry's body, which is never replaced.
        links: slugs of the entries this one is about, each carried by an entry.
          A link no entry carries is refused and nothing is written.
        aliases: other names it goes by, so a search by names finds it.
        details: the type's own fields.
        source: how the information arrived, in a word.
        """
        return {"id": entries.write(
            type=type, version=version, entry=entry, slug=slug, event_date=event_date,
            description=description, body=body, links=links, aliases=aliases or [], details=details,
            source=source,
        )}

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def search(
        pattern: str | None = None,
        slugs: list[str] | None = None,
        names: list[str] | None = None,
        types: list[str] | None = None,
        event_date_from: str | None = None,
        event_date_to: str | None = None,
        recorded_after: str | None = None,
        details: dict[str, str] | None = None,
        newest_first: bool = False,
    ) -> dict:
        """Finds entries of every type and returns {"hits": [...]}, each hit's id, type,
        slugs, event_date, recorded_at, description, snippet, and the names that found
        it. Read full text with `read`.

        pattern: words to find, in any case, in the description, body, or an
          amendment. Every word must appear, in any form of it; a "quoted phrase"
          as written; a word ending in * as a prefix; one starting with - must not
          appear; OR between terms finds either side.
        slugs: finds the entries carrying any of them and every entry linking to
          them, through any merge.
        names: what something is called, as anyone might put it; finds for each
          up to five entries of the given types whose slug, alias, or description
          matches it in any case, held whole as words, or spelled alike. Needs types.
        Given more than one of pattern, slugs, and names, an entry is a hit when
        any finds it, so pass the subjects' slugs plus words for wording they might miss.
        types: the kinds of entry to keep. event_date_from, event_date_to:
          YYYY-MM-DD, inclusive. recorded_after: a UTC time or date; finds entries
          recorded or revised after it. details: a type's own fields, matched exactly.
        Hits are in event-date order, oldest first unless newest_first. A search
        that finds more than 100 returns none and fails with how to refine it,
        including event-date ranges that each fit; to cover everything on a
        subject, search each of those ranges.
        """
        hits = reader.search(
            pattern, slugs=slugs, names=names, types=types, event_date_from=event_date_from,
            event_date_to=event_date_to, recorded_after=recorded_after, details=details,
            newest_first=newest_first,
        )
        return {"hits": [asdict(hit) for hit in hits]}

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def read(ids: list[str]) -> str:
        """Returns the entries for a list of ids, in event-date order, as Markdown.

        Each entry opens with its description as a heading, then a line of its
        fields (id, type, event_date, recorded_at, source), then its slugs,
        aliases, and links, the entry it is merged into if any, and its details,
        then its body as written. An entry comes as it stands now, with its
        revisions applied and its amendments, oldest first, under a body that is
        never replaced. Entries are separated by a line of ---. A revision's id
        reads the entry it belongs to. An id not found is left out. Read only
        the ids a search picked out.
        """
        return render(reader.read(ids))

    return server


def main() -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s: %(message)s")
    try:
        brain = brain_dir()
        data, why = data_dir(brain)
    except FolderError as error:
        log.error("%s", error)
        return 1
    log.info("Brain folder %s; plugin data folder %s (%s)", brain, data, why)
    build(brain, data).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
