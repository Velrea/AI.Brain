# Extending the Brain

The Brain is a knowledge store. A workflow of your own, such as a research method or a hunt for something, lives outside it and records what it finds through the plugin's skills. Most never need anything more.

## Record through the plugin's skills

| What you have | Record it with |
| --- | --- |
| A person, company, place, thing, or topic you keep coming back to | `entity` |
| Something that happened, or something you found | `journal`, linked to what it is about |
| An answer you keep current, such as a profile or a shortlist | `snapshot` |
| A file, or a link to content kept elsewhere | `document` |

`query` answers from all of it.

## Write a workflow

1. Keep the method where you keep your work: a skill of your own, a project's files, or a note. Not in the Brain.
2. Say in it what to record, and with which skill.
3. Link every entry to the entities it is about, so a search by one returns everything about it.

A workflow that is a skill goes where the plugin is installed:

| Plugin installed with | Put the skill in |
| --- | --- |
| `--scope user`, the default | `~/.claude/skills/<name>/SKILL.md` |
| `--scope project` or `--scope local` | `<project>/.claude/skills/<name>/SKILL.md` |

Example, `~/.claude/skills/breeder-scout/SKILL.md`:

```markdown
---
name: breeder-scout
description: "Scouts teacup-dragon breeders and records what it finds in the Brain."
when_to_use: "The user asks to scout, find, or vet teacup-dragon breeders."
---

1. Search the breeder registries and the forums for breeders taking new clients.
2. For each breeder: record it with `entity` if the Brain has no entry for it yet.
3. Find who runs it, how long it has bred, and what its customers say. Record the findings with `journal`, linked to the breeder.
4. Update the shortlist with `snapshot`, linked to every breeder on it.
```

## A type of your own

Only when you must find entries by a value that words cannot, such as which tasks are still open.

- The type is a slug, never `journal`, `entity`, `snapshot`, or `document`. Its version starts at 1.
- The description and body carry everything a reader needs. `query` reads them without your skill.
- `details` holds only values to search by exactly.
- Change an entry by revising it with its id, never by writing a second one.
- Never write, edit, move, or delete files in the Brain folder, or import the plugin's Python.

The tools are `mcp__plugin_brain_brain__write`, `__search`, and `__read`.

| `write` field | To create | To revise |
| --- | --- | --- |
| `type`, `version` | required | required, the entry's own |
| `entry` | left out | the entry's id |
| `slug` | required: lowercase words joined by hyphens, unique | adds a name |
| `event_date` | required, `YYYY-MM-DD` | replaces it |
| `description` | required, one line | replaces it |
| `body` | required, Markdown | kept under the original as an amendment |
| `links` | slugs of entries it is about | replaces them |
| `aliases` | other names it goes by | adds to them |
| `details` | a JSON object | replaces each field given; `null` removes one |

`search` takes `pattern` (words), `slugs`, `names` (with `types`), `types`, `event_date_from`, `event_date_to`, `recorded_after`, `details` (matched exactly), and `newest_first`, and returns lean hits; past 100 it fails with date ranges to search instead. `read` takes `ids` and returns those entries whole.

Example, `~/.claude/skills/task/SKILL.md`:

````markdown
---
name: task
description: "Records a task, marks one done, and lists what is open."
when_to_use: "The user asks to add, finish, or list tasks."
---

## Add

Find its subjects: `search` by `names`, `types: ["entity"]`. Then `write`:

```
type: task
version: 1
slug: <a few words>
event_date: <today>
description: <the task, one line>
body: <what is to be done, by when, and for whom>
links: <its subjects>
details: {"status": "open"}
```

## Done

`search` by its words, `types: ["task"]`, `details: {"status": "open"}`. Then `write`:

```
type: task
version: 1
entry: <its id>
body: <when and how it was finished>
details: {"status": "done"}
```

## List

`search` with `types: ["task"]`, `details: {"status": "open"}`. `read` the ids, and list each with what it is for and by when.
````
