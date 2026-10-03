---
name: snapshot
description: "Records a folded answer so it need not be recomputed."
when_to_use: "The user agrees to keep an answer that took many entries to fold, or asks to snapshot, save, or keep an answer."
argument-hint: "[the question it answers]"
---

Only at the user's word. Build the answer from every matching entry, never from an earlier snapshot.

```
type: snapshot
version: 1
slug: <the scope>-<YYYY-MM-DD>
event_date: <today>
description: <one-line summary of the answer>
body: <the answer, citing each entry by date and description>
links: <subjects it covers>
details: {"scope": "<the question's meaning in a few words, worded so paraphrases match>"}
```

Slug taken: add words.
