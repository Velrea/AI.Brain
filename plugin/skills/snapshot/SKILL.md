---
name: snapshot
description: "Records a folded answer so it need not be recomputed."
when_to_use: "The user agrees to keep an answer that took many entries to fold, or asks to snapshot, save, or keep an answer."
argument-hint: "[the question it answers]"
---

A snapshot keeps an answer that took many entries to fold, so a later question starts from it. Write one only at the user's word.

## Build it

Build the answer afresh from every entry that bears on it, never from an earlier snapshot, so a record that synced late or was misread when that one was folded is caught.

## Record it

Record it with `write`:

- `type`: `snapshot`
- `version`: `1`
- `slug`: `<the scope as a slug>-<today, YYYY-MM-DD>`
- `event_date`: `<today, YYYY-MM-DD>`
- `description`: `<one line summarizing the answer>`
- `body`: `<the answer, in Markdown, with the date and description of each entry it rests on>`
- `links`: `<the slugs of the subjects it covers>`
- `details`: `{"scope": "<the question's meaning in a few words, put so paraphrases of the question land on the same scope>"}`

A slug already taken means a snapshot of this scope was taken today: give this one more words.
