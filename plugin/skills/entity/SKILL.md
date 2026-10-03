---
name: entity
description: "Records a subject entries are about, adds a name to one, or merges two that turn out to be one."
when_to_use: "A person, thing, or topic to record, rename, or give another name; two subjects that turn out to be one; and a request to merge or tidy duplicate subjects."
argument-hint: "<the subject>"
---

An entity is a person, thing, or topic that outlasts any one event. Entries link to it by slug, so a search by its slug finds every entry about it.

## Find it first

Search by `names`, with `types` of `entity`, passing every name the subject goes by. Reuse a match. Ask the user about a match that is plausible but uncertain: a wrong match merges two real things, and a needless new entity splits one.

## Record it

Record a subject with no match with `write`:

- `type`: `entity`
- `version`: `1`
- `slug`: `<its name as a slug>`
- `event_date`: `<today, YYYY-MM-DD>`
- `description`: `<its name>`
- `body`: `<what it is, in a line or two>`
- `aliases`: `<every other name it goes by>`
- `details`: `{"kind": "<what sort of thing it is, in a word>"}`

A slug already taken means a match was missed: search again, or give it a slug that tells the two apart.

## Another name

A name the subject also goes by is a `write` revising it:

- `type`: `entity`
- `version`: `1`
- `entry`: `<its id>`
- `aliases`: `<the new names>`

Change its name, what it is, or its kind the same way, with `description`, `body` as an amendment, or `details`.

## Two that are one

Deciding that two entities are one is judgment: ask the user unless they asked for the merge. Keep the one more entries link to, and merge the other into it with one `write`:

- `type`: `entity`
- `version`: `1`
- `entry`: `<the id of the one kept>`
- `slug`: `<the slug of the other>`
- `aliases`: `<the other's name and aliases>`

That one record is the whole merge: every entry linking to either slug is found by both, including entries that sync in later, and the other no longer turns up in a search.
