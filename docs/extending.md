# Extending the Brain

The plugin's skills record journal entries, entities, snapshots, and filed documents, and answer from them. A use with behavior of its own, such as a ledger, a research topic, or a job search, is built as a skill of your own on the same tools, kept in your own setup: a personal skill in `~/.claude/skills/<name>/SKILL.md`, or a project's in `.claude/skills/`. The plugin ships no skill for a particular use, since one person's ledger is not another's.

## The tools

A skill reaches the Brain through [the MCP server's](mcp-server.md) three tools, the same ones the plugin's skills use, named `mcp__plugin_brain_brain__write`, `__search`, and `__read`:

| Tool | Does |
| --- | --- |
| `write` | creates an entry of any type, or revises one given its id |
| `search` | finds entries by words, slugs, names, type, event date, recorded time, and `details` fields |
| `read` | returns entries by id, whole, with their amendments |

Never import the core module's Python instead. It lives in the plugin's install folder, which every update replaces; it runs in the plugin's own environment; and writing through it skips the checks the tools carry. No tool is for a particular type, so a new type needs no change to the server or the core module.

## Define a type

A skill defines its type the way [the plugin's skills](skills.md) do: it gives `write` the type and version as fixed values, and leaves placeholders for the model to fill. Everything the type adds goes in `details`; the envelope's fields mean the same for every type. A skill for a hoard ledger might hold:

```
type: hoard-ledger
version: 1
slug: <YYYY-MM-DD>-<what came in or went out>
event_date: <the day it happened>
description: <one line: what changed and by how much>
body: <what happened, every value as given>
links: <the hoard's entity, and anyone involved>
details: {"coins": <the change, negative when spent>, "currency": "<the coin>"}
```

- **The type is a slug of its own**, never `journal`, `entity`, `snapshot`, or `document`, which the plugin's skills define.
- **The version starts at 1.** Raise it when the shape of `details` changes, and have the skill read every version it has written, since entries are never rewritten.
- **Leave the tools' rules to the tools.** A slug already taken, a link no entry carries, a bad date, or a revision of another type's entry is refused with a message saying what to do; the skill need not restate any of it.

## What to record

- **One entry per event**, such as a payment, an interview, or a reading, never one entry kept current. The Brain holds events, and how things stand now is worked out by reading them in order.
- **Link every entry to an entity for its subject**, such as the hoard, the company applied to, or the topic researched, so one search by that entity's slug returns the whole set. Record a missing subject through the `entity` skill.
- **A running answer is a snapshot**, such as a balance or a shortlist, written through the `snapshot` skill at the user's word, with a scope that names the question.
- **A file is a filed document.** Hand it to the `document` skill, and link the document entry from your own.
- **A correction is a revision** of the entry that got it wrong, given its id: changed fields replace the entry's, and a body is kept as an amendment under the original, never in place of it.
- **What the user would want in their journal** goes through the `journal` skill too, linking your entries, so a question about what happened finds it.

## Find and fold

- **Search by the subject's slug and your type**, `newest_first` for the latest; filter by event dates, or by a `details` field, which matches exactly.
- **Read only the ids you pick**, a few long entries at a time, and fold them in event-date order, a later entry superseding an earlier one.
- **A search past the ceiling of 100 hits** fails with event-date ranges to search instead; search each, folding as you go.
- **Start from a snapshot** where one fits the question, and fold in what was recorded after it.

The `query` skill searches every type, so a question asked without your skill already finds your entries; your skill carries what only it knows, such as how to total a ledger.

## Leave alone

- **The Brain folder's files.** Never write, edit, move, or delete anything in `events/`; the tools are the only writers. Files in `documents/` belong to the `document` skill.
- **The plugin's install folder**, which every update replaces.
- **The document skill's script.** It is given folders only the plugin's own skills are told, so hand files to `document` rather than calling it.
