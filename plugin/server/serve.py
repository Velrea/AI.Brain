"""The Brain's MCP server, over stdio: the core module's type methods, its
reads, and its documents store, each as a tool.

It holds no logic about the data: every tool calls the core module, and
each tool's description carries the rules the call enforces, so an agent
without the skills behaves the same. A failure the model can act on, such
as an unknown entity or a search that finds too much, comes back as an
error result with how to put it right.
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

from brain.documents import Documents
from brain.entries import Entries
from brain.format import RecordError
from brain.lock import LockTimeout
from brain.read import Reader
from brain.write import AppendBlocked, Writer
from server.folders import FolderError, brain_dir, data_dir

log = logging.getLogger("brain")

INSTRUCTIONS = """\
The Brain is the user's own record of their life: an append-only log of journal \
entries, the entities they are about, snapshots of folded answers, and filed \
documents. Nothing is ever edited; a correction is a revision. Find with `search`, \
then `read` only the ids you pick. Resolve names to entities with `resolve` before \
writing or searching by them."""

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
    details = dict(record["details"])
    fields = [f"{name}: {record[name]}" for name in ("id", "type", "event_date", "recorded_at", "source") if record.get(name)]
    lines = [f"# {record['description']}", " | ".join(fields)]
    if entities := details.pop("entities", None):
        lines.append("entities: " + ", ".join(entities))
    for document in details.pop("documents", None) or []:
        lines.append(f"document: {document['path']} (sha256 {document['sha256']})")
    for name, value in details.items():
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
    documents = Documents(brain)
    server = MCPServer("brain", instructions=INSTRUCTIONS)

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def write_journal(
        event_date: str,
        description: str,
        body: str,
        entities: list[str] | None = None,
        documents: list[dict[str, str]] | None = None,
        source: str | None = None,
    ) -> dict:
        """Records a journal entry, an account of something that happened, and returns {"id": ...}.

        event_date: when it happened, a local date, YYYY-MM-DD.
        description: one line a reader can triage from without opening the entry,
          such as "Oil change at 48k, rear brakes flagged as worn".
        body: Markdown, the account itself, as complete as it was given.
        entities: slugs of the entities the entry is about, each one already
          recorded. Resolve each subject first; write an entity only when none
          matches. An unrecorded slug is refused and nothing is written.
        documents: the filed documents the entry is about, each {"path": ..., "sha256": ...}
          exactly as store_document returned it. File each document first.
        source: how the information arrived, such as voice or email.
        """
        return {"id": entries.write_journal(
            event_date=event_date, description=description, body=body,
            entities=entities or [], documents=documents or [], source=source,
        )}

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def revise_journal(
        entry: str,
        description: str | None = None,
        event_date: str | None = None,
        entities: list[str] | None = None,
        amendment: str | None = None,
        source: str | None = None,
    ) -> dict:
        """Corrects a journal entry and returns the revision's {"id": ...}.

        entry: the id of the original entry.
        description, event_date, entities: each given replaces the entry's; each
          left out stands. entities replaces the whole list, each slug recorded.
        amendment: text kept under the entry's body, such as "Correction: it was
          three drops, not two." The body itself is never replaced.
        A revision must change something or add an amendment.
        """
        return {"id": entries.revise_journal(
            entry, description=description, event_date=event_date,
            entities=entities, amendment=amendment, source=source,
        )}

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def write_entity(
        slug: str,
        name: str,
        kind: str,
        body: str,
        aliases: list[str] | None = None,
        source: str | None = None,
    ) -> dict:
        """Records an entity, a person, thing, or topic entries are about, and returns {"id": ...}.

        slug: how entries name it: lowercase words joined by hyphens, such as dr-jekyll.
        name: what it is called, one line. kind: what sort of thing it is, such as
          person or medication. body: Markdown, what it is. aliases: other names it
          goes by, so `resolve` finds it by them.
        Writing a slug already recorded restates that entity: its name, kind, and
        body become these, and the aliases add to those it has. Resolve first, so
        a subject is recorded once.
        """
        return {"id": entries.write_entity(
            slug=slug, name=name, kind=kind, body=body, aliases=aliases or [], source=source,
        )}

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def write_snapshot(scope: str, description: str, body: str) -> dict:
        """Records a folded answer so it need not be recomputed, and returns {"id": ...}.
        Write one only when the user agrees to it.

        scope: the question's meaning, one line, put so paraphrases land on one
          scope, such as "current medications".
        description: one line summarizing the answer. body: Markdown, the answer.
        Its event date is today. To use one later, search for the latest with this
        scope, then for what was recorded or revised after it, reaching back a few
        days for entries that synced late, and fold those in.
        """
        return {"id": entries.write_snapshot(scope=scope, description=description, body=body)}

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def search(
        pattern: str | None = None,
        entities: list[str] | None = None,
        types: list[str] | None = None,
        event_date_from: str | None = None,
        event_date_to: str | None = None,
        recorded_after: str | None = None,
        details: dict[str, str] | None = None,
        newest_first: bool = False,
    ) -> dict:
        """Finds entries of every type and returns {"hits": [...]}, each hit's id, type,
        event_date, recorded_at, description, and snippet. Read full text with `read`.

        pattern: words to find, in any case, in the description, body, or an
          amendment. Every word must appear, in any form of it; a "quoted phrase"
          as written; a word ending in * as a prefix; one starting with - must not
          appear; OR between terms finds either side.
        entities: slugs; an entry naming any of them is a hit, and so is the
          entity. Given with pattern, an entry is a hit when either finds it, so
          pass the subjects' slugs plus words for wording they might miss.
        types: such as journal, entity, snapshot. event_date_from, event_date_to:
          YYYY-MM-DD, inclusive. recorded_after: a UTC time or date; finds entries
          recorded or revised after it. details: a type's own fields, matched exactly.
        Hits are in event-date order, oldest first unless newest_first. A search
        that finds more than 100 returns none and fails with how to refine it,
        including event-date ranges that each fit; to cover everything on a
        subject, search each of those ranges.
        """
        hits = reader.search(
            pattern, types=types, event_date_from=event_date_from, event_date_to=event_date_to,
            recorded_after=recorded_after, details=details, entities=entities, newest_first=newest_first,
        )
        return {"hits": [asdict(hit) for hit in hits]}

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def read(ids: list[str]) -> str:
        """Returns the full records for a list of ids, in event-date order, as Markdown.

        Each record opens with its description as a heading, then a line of its
        fields (id, type, event_date, recorded_at, source), then the entities and
        documents it names and any other details, then its body as written. An
        entry comes as it stands now, with its revisions applied and its
        amendments, oldest first, under a body that is never replaced; an entity
        as its statements hold it now. Records are separated by a line of ---.
        A revision's id reads the entry it belongs to. An id not found is left
        out. Read only the ids a search picked out.
        """
        return render(reader.read(ids))

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def resolve(names: list[str]) -> dict:
        """Returns {"matches": {name: [...]}}: for each name, up to five likely entities,
        best first, each its id, slug, name, kind, and aliases, or none when nothing
        is likely.

        Pass every subject an entry or a question names, at once. A name matches
        an entity's slug, name, or an alias in any case and punctuation, held whole
        as words, or spelled alike. Shorthand that spells nothing like the name is
        found only through an alias.
        """
        found = reader.resolve(names)
        return {"matches": {name: [asdict(entity) for entity in matches] for name, matches in found.items()}}

    @server.tool(annotations=WRITES, structured_output=False)
    @_tool
    def store_document(source: str, path: str) -> dict:
        """Files a copy of a document into the Brain and returns {"path": ..., "sha256": ...}.

        source: the file to copy, a path on this machine. It is left where it is.
        path: where it is filed inside the Brain's documents, relative, with /
          between folders, such as "car/2026-09-14 oil change invoice.pdf".
        Filing the same contents at a path again returns it as it is; a path that
        already holds other contents is refused. File the document first, then
        pass what this returns in write_journal's documents.
        """
        return documents.store(Path(source), path)

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
