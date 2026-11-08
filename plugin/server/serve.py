"""The Brain's MCP server, over stdio: the core module's write, search, and
read, and its filing of documents, each as a tool, beside `configure` and
`status` for the install itself.

It starts whatever is wrong with the Brain folder, so the user hears what is
wrong in the conversation instead of finding the tools missing.

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
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict
from importlib import metadata
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from brain.documents import Documents
from brain.format import RecordError
from brain.index import FileHeld
from brain.lock import LockTimeout
from brain.read import Reader
from brain.write import AppendBlocked, Writer
from server.folders import (
    PLUGIN, BrainMissing, FolderError, NotConfigured, brain_setting, data_dir, existing, host_path,
)
from server.folders import configure as configure_folder

log = logging.getLogger("brain")

INSTRUCTIONS = """\
The Brain is the user's journal of whatever they choose to record: an append-only \
log of entries, each of a type its skill defines, named by slugs and linked to other \
entries by slug. Nothing is ever edited; a correction is a \
revision through `write`. Find with `search`, then `read` only the ids you pick. \
Search by names for the slugs of what you mean before linking to or searching by them."""

READS = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
WRITES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
CONFIGURES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
FILES = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
"""Filing can remove the original, so a host that asks before a destructive tool asks."""

REQUIREMENTS = PLUGIN / "requirements.in"
"""The packages the server names; `requirements.txt` pins them and all they need."""

# Failures the model can put right, or retry: each comes back as an error result.
_ANTICIPATED = (RecordError, ValueError, LockTimeout, AppendBlocked, FileHeld)


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


class Folders:
    """The folders the tools work in, and what keeps the Brain from being used."""

    def __init__(self, data: Path, data_why: str, environ: Mapping[str, str]):
        self.data, self.data_why, self.environ = data, data_why, environ
        self.load()

    def load(self) -> None:
        """Finds the Brain folder again, and opens it when nothing is wrong."""
        self.brain, self.brain_why, self.problem = None, "not configured", None
        self.reader = self.writer = self.documents = None
        try:
            self.brain, self.brain_why = brain_setting(self.data, self.environ)
            if self.brain is None:
                raise NotConfigured("no Brain folder is configured")
            brain = existing(self.brain)
            data_dir(brain, {"PLUGIN_DATA": str(self.data)})
        except FolderError as error:
            self.problem = error
            log.warning("%s", error)
            return
        self.reader, self.writer = Reader(brain, self.data), Writer(brain, self.data)
        self.documents = Documents(brain, self.reader)
        log.info("Brain folder %s (%s)", brain, self.brain_why)

    def ready(self) -> tuple[Reader, Writer, Documents]:
        """The reader, writer, and documents, or an error result saying what is wrong and how to put it right."""
        if self.problem is not None:
            raise ToolError(guidance(self.problem))
        return self.reader, self.writer, self.documents


def guidance(problem: FolderError) -> str:
    """What the model is told when the Brain cannot be used."""
    if isinstance(problem, NotConfigured):
        return ("The Brain is not set up: no Brain folder is configured. Ask the user for the folder that holds"
                " their Brain, or where to start a new one, and call `configure` with it.")
    if isinstance(problem, BrainMissing):
        return (f"The Brain folder {str(problem.path)!r} does not exist: its sync folder may not be available."
                " Ask the user whether to create it. Told yes, call `configure` with this folder and `create`."
                " Told no, say the Brain cannot be used until the folder exists or another is configured,"
                " and do nothing more with it.")
    return f"The Brain cannot be used: {problem}. Tell the user what is wrong and how to fix it."


def build(data: Path, environ: Mapping[str, str] = os.environ, data_why: str = "given") -> MCPServer:
    """The server, keeping this install's files in `data`. It starts whatever is
    wrong with the Brain folder, and every tool but `configure` and `status`
    answers with what is wrong until it is put right."""
    folders = Folders(data, data_why, environ)
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
        _, writer, _ = folders.ready()
        return {"id": writer.write(
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
        reader, _, _ = folders.ready()
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
        reader, _, _ = folders.ready()
        return render(reader.read(ids))

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def list_documents(folder: str = "") -> dict:
        """Lists one folder of the Brain's filed documents and returns {"folders": [{"name",
        "documents"}], "documents": [...]}: its subfolders, each with how many documents it
        holds at any depth, and the documents directly in it, in name order.

        folder: a path inside the filed documents, folders joined by /; empty for the top.
        """
        _, _, documents = folders.ready()
        return documents.browse(folder)

    @server.tool(annotations=FILES, structured_output=False)
    @_tool
    def store_document(file: str, path: str, move: bool = False) -> dict:
        """Files the document at `file` into the Brain's documents at `path`, and returns
        {"path", "sha256"} for its entry's details.

        file: the absolute path of the file to file.
        path: where it goes inside the filed documents, folders joined by /, which are
          created as needed. No name in it is empty, . or .., ends in a dot or a space,
          or holds a backslash or any of <>:"|?*.
        move: removes the original, only once its copy is in place. An original that
          cannot be removed fails with the path and sha256 it was filed under.
        Refuses contents a document entry already names, a path that holds other
        contents, and a file already in the filed documents, which is checked instead.
        Filing the same contents at the same path again returns it as it is.
        """
        _, _, documents = folders.ready()
        source = host_path(file)
        if not source.is_absolute():
            raise ToolError(f"{file!r} is not an absolute path: give the file's full path")
        return documents.store(source, path, move=move)

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def check_documents(path: str = "") -> dict:
        """Reports how the filed documents at `path` differ from their entries, and returns
        {"changed", "moved", "missing", "unrecorded"}, each in path order:
        changed, [{"path", "entry", "sha256"}]: contents not the ones its entry names,
          with their sha256 now.
        moved, [{"entry", "from", "to"}]: an entry's document gone from its path, with the
          same contents at a path no entry names.
        missing, [{"path", "entry"}]: an entry's document gone, its contents nowhere checked.
        unrecorded, [{"path", "sha256"}]: a document no entry names.

        path: a folder or one document inside the filed documents, folders joined by /;
          empty for every one. Each document checked is read whole, so check no more than
          asked.
        """
        _, _, documents = folders.ready()
        return documents.check(path)

    @server.tool(annotations=CONFIGURES, structured_output=False)
    @_tool
    def configure(folder: str, create: bool = False) -> dict:
        """Sets the folder that holds the user's Brain, kept for this install, and returns
        {"brain_folder": ...}. Called again, it changes the folder.

        folder: the absolute path of the folder the user names.
        create: creates the folder when it does not exist. Pass it only once the user
          has said to create it; without it, a folder that does not exist is refused.
        """
        try:
            path = configure_folder(folders.data, folder, create=create, environ=folders.environ)
        except FolderError as error:
            raise ToolError(str(error)) from error
        folders.load()
        return {"brain_folder": str(path)}

    @server.tool(annotations=READS, structured_output=False)
    @_tool
    def status() -> dict:
        """Reports how this install of the Brain is set up: {"brain_folder", "brain_folder_from",
        "problem", "data_folder", "data_folder_from", "python", "packages"}. "problem" is
        what keeps the Brain from being used, or null."""
        return {
            "brain_folder": None if folders.brain is None else str(folders.brain),
            "brain_folder_from": folders.brain_why,
            "problem": None if folders.problem is None else guidance(folders.problem),
            "data_folder": str(folders.data),
            "data_folder_from": folders.data_why,
            "python": f"{sys.version.split()[0]} at {sys.executable}",
            "packages": packages(),
        }

    return server


def packages() -> dict[str, str | None]:
    """The installed version of each package the server names in `requirements.in`."""
    names = [line.split("==")[0].strip() for line in REQUIREMENTS.read_text("utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    found = {}
    for name in names:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            found[name] = None
    return found


def main() -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s: %(message)s")
    try:
        data, why = data_dir(None)
    except FolderError as error:
        log.error("%s", error)
        return 1
    log.info("plugin data folder %s (%s)", data, why)
    build(data, os.environ, why).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
