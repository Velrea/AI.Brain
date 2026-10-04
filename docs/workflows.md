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

### Keep track of dragon breeders

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

### Keep a ledger for a market day

`~/.claude/skills/bazaar-ledger/SKILL.md`:

```markdown
---
name: bazaar-ledger
description: "Keeps a ledger of a day at the goblin bazaar and records it in the Brain at close."
when_to_use: "The user starts a day at the goblin bazaar, buys or sells something there, or closes out the day."
---

1. Keep a table in the conversation: the time, the stall, the item, and what was paid or taken.
2. Add a row for every purchase and sale, and show the running total.
3. At close, record the day with `journal`: the table and the day's total, linked to the bazaar and every stall in it.
```

### Follow a question over time

`~/.claude/skills/harvest-watch/SKILL.md`:

```markdown
---
name: harvest-watch
description: "Follows how the moonberry harvest is shaping up, and records what is new in the Brain."
when_to_use: "The user asks how the moonberry harvest is going, or to check on it."
---

1. `query` the Brain for the latest snapshot of the harvest, and what was recorded since.
2. Check the growers' reports and the market prices for anything newer.
3. Record what is new with `journal`, linked to the moonberry harvest entity.
4. Update the current outlook with `snapshot`, and say what changed.
```
