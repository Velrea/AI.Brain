---
name: entity
description: "Records a subject entries are about, adds a name to one, or merges two that turn out to be one."
when_to_use: "A person, thing, or topic to record, rename, or give another name; two subjects that turn out to be one; and a request to merge or tidy duplicate subjects."
argument-hint: "<the subject>"
---

An entity is a person, thing, or topic that outlasts one event.

## Find

`search` by every name it goes by, `types: ["entity"]`. Reuse a match. Ask about an uncertain one.

## Create

```
type: entity
version: 1
slug: <its name>
event_date: <today>
description: <its name>
body: <what it is, a line or two>
aliases: <its other names>
details: {"kind": "<what sort of thing, one word>"}
```

Slug taken: search again; else choose a slug that tells the two apart.

## Change

Revise with `entry: <its id>`: `aliases` adds names; `description`, `details`, or an amendment `body` changes the rest.

## Merge

Only at the user's word. Keep the one more entries link to:

```
type: entity
version: 1
entry: <id of the one kept>
slug: <slug of the other>
aliases: <the other's names>
```
