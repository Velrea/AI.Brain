# Custom workflows

The Brain is a knowledge store. A workflow of your own, such as a research method, a hunt for something, or a ledger you keep for a day, lives outside it and records what it finds through the plugin's skills.

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

## Examples

### Scout dragon breeders

`~/.claude/skills/dragon-breeder-scout/SKILL.md`:

```markdown
---
name: dragon-breeder-scout
description: "Scouts dragon breeders and records what it finds in the Brain."
when_to_use: "The user asks to scout, find, or vet dragon breeders."
---

1. Search the breeder registries and the forums for breeders taking new clients.
2. For each breeder: record it with `entity` if the Brain has no entry for it yet.
3. Find who runs it, how long it has bred, and what its customers say. Record the findings with `journal`, linked to the breeder.
4. Update the shortlist with `snapshot`, linked to every breeder on it.
```

### Keep a ledger for a day

At the goblin bazaar, every purchase and sale goes into a table kept in the conversation: the stall, the item, what was paid or taken. At the end of the day, one `journal` entry records the table and the day's total, linked to the bazaar.

### Follow a question over time

A note holds the question, such as how the moonberry harvest is shaping up, and where to look. Each run records what is new with `journal`, linked to a topic entity for the question, and updates the current answer with `snapshot`.
