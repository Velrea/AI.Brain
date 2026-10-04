---
name: journal
description: "Records what happened as a journal entry, or corrects one."
when_to_use: "The user asks to journal, record, note, or correct something, or mentions in passing something that has happened or is planned that they would want to recall later."
argument-hint: "[the event to record]"
---

Record what happened so a reader months later can follow it.

## When

- Asked: record.
- Unprompted: record what the user took part in that has happened. Offer first for what they only observed, what is planned, or what you found.
- Never record the session's own work.

## Before writing

- Ask only where a reader months later could not follow what happened: something the account depends on and leaves out or leaves unclear, never detail it could hold but does not need. Never guess a date, name, or figure. A complete account is written as given.
- Find every subject and the broad subject it falls under: one `search` by `names`, `types: ["entity"]`. Record missing subjects and new names through `entity`. Ask about an uncertain match.
- Read the newest entry on the same subject (`search` by its slug, `types: ["journal"]`, `newest_first`); follow its layout.

## Write

```
type: journal
version: 1
slug: <YYYY-MM-DD>-<a few words>
event_date: <the day it happened>
description: <one line: what happened and what about it matters>
body: <what happened, every value as given, everyone by name; decisions, commitments with owner and date, open questions>
links: <subjects, document entries, the entry it follows on from>
source: <how it arrived, one word>
```

- One event per entry.
- Keep every link or reference to more of the account.
- Never write a secret in full.
- Slug taken: add words.

## Documents

From `document`: one entry summarizing what was captured and what surrounds it, linking each document entry. Ask only what the documents leave unclear. Date it by the event, else the capture day. One entry per event.

## Corrections

What the entry got wrong: revise it.

```
type: journal
version: 1
entry: <its id>
body: <what was wrong, what is right>
description, event_date, links: <only what changes>
```

What the entry never held: a new entry linking to it. Both: both.
