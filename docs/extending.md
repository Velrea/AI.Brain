# Extending the Brain

Add a use the plugin does not cover by writing a skill of your own that records entries through the Brain's tools.

## 1. Put the skill where the plugin is installed

| Plugin installed with | Put the skill in |
| --- | --- |
| `--scope user`, the default | `~/.claude/skills/<name>/SKILL.md` |
| `--scope project` or `--scope local` | `<project>/.claude/skills/<name>/SKILL.md` |

## 2. Write the skill

- Pick a type: a slug, never `journal`, `entity`, `snapshot`, or `document`.
- Give `write` the type and `version: 1` as fixed values, and a placeholder for every other field.
- Put everything a reader needs in `description` and `body`.
- Put a value in `details` only to search by it exactly.
- Link each entry to the entities it is about. Record a missing one with the `entity` skill.
- Change an entry by revising it, never by writing a second one.

## 3. Use the tools

Every skill uses the same three tools, named `mcp__plugin_brain_brain__write`, `__search`, and `__read`.

**`write`** creates an entry, or revises one, and returns its `id`.

| Field | To create | To revise |
| --- | --- | --- |
| `type`, `version` | required | required, the entry's own |
| `entry` | left out | the entry's id |
| `slug` | required: lowercase words joined by hyphens, carried by no other entry | adds a name |
| `event_date` | required, `YYYY-MM-DD` | replaces it |
| `description` | required, one line | replaces it |
| `body` | required, Markdown | kept under the original as an amendment |
| `links` | slugs of entries it is about | replaces them |
| `aliases` | other names it goes by | adds to them |
| `details` | the type's own fields, a JSON object | replaces each field given; `null` removes one |
| `source` | how it arrived, one word | |

**`search`** returns lean hits: each one's `id`, `type`, `slugs`, `event_date`, `recorded_at`, `description`, and a snippet.

| Field | Finds |
| --- | --- |
| `pattern` | words in the description, body, or amendments |
| `slugs` | the entries carrying them, and every entry linking to them |
| `names` | up to five entries per name whose slug, alias, or description matches; needs `types` |
| `types` | only entries of these types |
| `event_date_from`, `event_date_to` | entries within these dates, inclusive |
| `recorded_after` | entries recorded or revised after this UTC time |
| `details` | entries whose fields match these exactly |
| `newest_first` | newest first, rather than oldest |

A search that finds more than 100 entries fails with event-date ranges to search instead.

**`read`** takes `ids` and returns those entries whole, as they stand now.

## 4. Try it

Start a new session and ask for what the skill does.

## Never

- Write, edit, move, or delete files in the Brain folder. Hand a file to the `document` skill.
- Import the plugin's Python, or change its files.

## Example: tasks

`~/.claude/skills/task/SKILL.md`:

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

Then: *"Add a task: re-trim the hovercart's left hover jets before the October float inspection."*
