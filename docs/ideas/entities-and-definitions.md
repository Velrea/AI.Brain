# Entities and definitions

Concerns the data format, writing, and reading.

- **An `entity` type** carries `slug`, `kind`, and `aliases` in its `details`: the durable things entries are about, which entries name by slug.
- **A `resolve` tool** turns a name into a few candidate entities.
- **User-defined types** are `definition` records, following the same pattern as the built-in `journal` and `snapshot`.

Open: the name a user-defined type goes by in the tools: type, extension, or kind.

## Tags

Searching free text cannot promise to find every entry on a subject: an entry that says "two drops of Moonberry extract with breakfast" never says "medication", and the model searching has to guess the words. Tags move that judgment to writing, when the model looks at one entry with its whole attention, so a later search by tag returns the whole set in one call.

- **Each entry carries tags** in its `details`: the people, things, and topics it is about, such as `medication`, `zorblax`, `dr-jekyll`, `mom`. Tags and entities may be one idea: a tag is an entity's slug.
- **Search ORs the pattern with the tags.** An entry is a hit when its text matches or it carries a tag asked for, so an entry tagged badly or not at all is still found by its words. Requiring both would lose it.
- **Writing keeps the tags consistent.** The journal agent loads the tags already in use, reuses one wherever it fits even when the entry words it differently, and adds a new one only when none fits. A command lists every tag in use with its count.
- **An audit consolidates them later**, a dreaming pass that looks through the tags and entities for duplicates, such as `meds` beside `medication`, and merges them.
- **Tags or entities could also be searched by meaning**, through embeddings, as [search and embeddings](search-and-embeddings.md) describes.

An experiment over a made-up decade of about 4,000 journal entries, with a fictional medication history hidden among them, asked three models which medications were current, and at what doses. Every entry was tagged as a careful agent would tag it.

| Setup | Haiku | Sonnet | Opus |
| --- | --- | --- | --- |
| Pattern search only | wrong (listed stopped drugs), 15 s | missed the Moonberry extract, 9 s | missed the Moonberry extract, 24 s |
| Tags offered, no guidance | wrong, 18 s | missed the Moonberry extract, 11 s | right, 18 s |
| Tags, with a line of guidance: list the tags, then one search by every fitting tag | right, 12 s | right, 12 s | right, 18 s |

- **Tags help only when the model uses them.** Offered tags without guidance, two of three models went back to guessing words. One line of guidance, which the query skill would carry, made all three right, the weakest model included.
- **Round trips cost more than the database.** Each search took well under a second; each model turn took one to three seconds. With guidance, every model answered in three or four turns.
- **Writing tags held up.** Given about 1,000 existing tags and twelve new entries worded loosely ("Dr. J doubled my Zorblax"), all three models put `medication` on every entry that needed it, mapped nicknames and shorthand such as "Dr. J" to the existing tag, `dr-jekyll`, and invented no duplicates; their new tags were for things the vocabulary lacked. They sometimes left out a broad tag such as `health`. The vocabulary cost about 8,000 tokens of input per write; a `resolve` step that narrows it would cut that.

These were single runs over generated data, with tags written by the generator, so they show the direction, not settled numbers.

Open: whether tags are a list in `details` or entities named by slug; whether the vocabulary is loaded whole or narrowed by a `resolve` step; how the audit merges a tag and rewrites nothing, since records are never edited.
