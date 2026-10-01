# Entities

The people, things, and topics entries are about, recorded as entities so a search can find every entry on a subject, not only the ones whose words it guesses. Promoted from the idea [entities and definitions](../ideas/entities-and-definitions.md), which holds the experiment behind it.

Searching free text cannot promise to find every entry on a subject: an entry that says "two drops of Moonberry extract with breakfast" never says "medication". Naming an entry's entities when it is written moves that judgment to the moment a model looks at one entry with its whole attention, and a later search by entity returns the whole set in one call. In the experiment, three models asked which medications were current, over a fictional decade of entries, missed or misstated a medication with text search alone, and all three answered fully once they searched by the entries' subjects.

It extends [the core module](../core-module.md), tested directly with no server, like reading. [The MCP server](mcp-server-and-launcher.md) then exposes it.

## Decided

- **An entity is an entry of type `entity`**, written through its own write method, never a separate list kept beside the log. A single list of every subject, loaded on every write, costs tokens that grow with the vocabulary; entities in the log are queried, so only the likely matches are loaded.
- **A journal entry names the entities it is about.**
- **Resolving takes a list of names and returns the likely matching entities for each**: a small subset of all of them, quick and cheap in tokens. The journal agent passes every subject it identifies in an entry, reuses an entity that matches, and creates one only when none does, so the same subject is never recorded twice.
- **Search matches the pattern or the entities.** An entry is a hit when its text matches or it names an entity asked for. Requiring both would lose an entry whose entities were missed when it was written.

## Done when

- An entity is written through its own method.
- A journal entry is written naming its entities.
- Resolving a list of names returns the likely matches for each, without loading every entity.
- `search` returns the entries that match the pattern or name any of the given entities.
- The tests drive the core module directly, with no server.

## Suggested

- **An entity carries a slug, a kind, and aliases** in its `details`, and entries name entities by slug, as the idea describes.
- **Resolve by name and alias first**, exact and then fuzzy, such as DuckDB's string similarity functions, and add search by meaning over entities only if that leaves duplicates. Meaning-based search needs an embedding model, which [search and embeddings](../ideas/search-and-embeddings.md) leaves open.
- **A command lists the entities in use**, with how many entries name each, for a query that starts by surveying the subjects.
