# Unified entries

Promoted from the idea Entity audit.

The Brain stores one thing, an entry, and a journal entry, an entity, and a snapshot are each an entry of a type. Today the core module adds a write method per type and the MCP server a tool per type, and entities are a mechanism of their own, so a new use means changing both layers. Instead every entry has the same shape, a name, and links to other entries; the core module keeps only what every entry obeys; the server exposes the same few calls for every type; and each type is defined by the skill that writes it. A skill someone writes for their own use then records its own type with no change to the core module or the server. It is done now, while it is cheap: before real data and other skills depend on the per-type tools.

## Decided

- **The MCP server is the translation layer** between the core module and the model's context, and nothing more. It exposes the core module's generic calls, a tool each, and no tool for a particular type, so it is never extended for a new one.
- **Three operations: write, search, and read.** `write_journal`, `write_entity`, `write_snapshot`, `revise_journal`, and `resolve`, and the per-type methods over the generic write in the core module, give way to them. Write takes the type, its version, and the type's own fields.
- **A skill defines its type.** It states the type and version as fixed values and has the model fill in the rest, succinctly. Journal, entity, and snapshot each have a skill that defines its type that way, and an extension is a skill that does the same.
- **The core module keeps what every entry has**: its id, its type, the date the event happened, when it was recorded, its slugs, and its links; and snapshots, as a mechanism every use can lean on.
- **The id is the identity.** The write path stamps each entry's UUIDv7, never the model.
- **Every entry has a slug**, a unique name the model gives it.
- **Entries link to entries by slug**, of any type, so a journal entry can link to another journal entry as well as to an entity. Links replace a journal entry's list of entities.
- **A write with no entry's id creates**, for something known to be new, and refuses a slug already recorded.
- **A write naming an entry's id revises it**, for every type, kept as an augmentation of the original: the original stands, and the revision is read with it.
- **An entry can carry more than one slug.** Two entries that turn out to be one thing, such as `meds` recorded beside `medication`, are merged by a revision that adds the old slug to the one kept. That is one record, revising none of the entries that link to the old slug, and the local index applies it when it builds, so entries linking to the old slug that sync in after the merge are covered with nothing more to write.
- **Deciding that two entries are one thing is judgment.** The model decides; the index only applies what was recorded.
- **Search finds by slug**, returning lean hits: each entry's id, slug, description, date, and the rest of what a hit carries now. Resolving names to entities is a search for entries of type entity.

## Suggested

- The refusal of a slug already recorded names the entry holding it, so the model can revise that entry instead.
- A search by name matches slugs, names, and aliases in any case, held whole as words, or spelled alike, as resolving does today, so a misspelled name or an alias still finds its entry, and shows which name found which entries.
- Two machines that each create one slug before they sync keep both entries; links by that slug find both, and a search shows both.
- Slugs and aliases accumulate across revisions rather than the newest replacing them, so two machines adding names before they sync lose neither.
- A journal entry's slug is its date and a few words.
- A snapshot keeps its scope as a field of its own, since each new snapshot of a question is a new entry and creating refuses a slug already recorded; or its slug carries its date.
- A filed document is an entry of type `document`, defined by its skill like any other type, with its path and `sha256` among its own fields. A journal entry links to it by slug rather than carrying a list of documents, a search by its fields finds it, replacing search's parameter for documents, and a changed document is a revision of its entry naming the new `sha256`. The intake skill defines the type.
- Filing stays an operation of its own, beside write, search, and read: moving a file into the documents folder, hashing it, and refusing contents already filed is work on the disk that no record can do. Listing a folder of documents may become a search of document entries by path.
- The core module still checks the fields the index reads: slugs, links, and aliases.
- A listing of the types and entities in use, with how many entries each has, shows a skill or a model what exists, and helps spot duplicates.
- An audit pass, a dreaming pass, looks through the entities for duplicates and proposes merges.
- Guidance on writing a particular type, such as a description a reader can triage from, moves from the tool's description to that type's skill. An agent without the skills still writes valid entries, but no longer writes a journal entry the way the journal skill would.

## Done when

- The MCP server's tools for entries are write, search, and read, and the core module has no write method for a particular type.
- The journal, entity, and snapshot skills each record their type through write.
- A write that creates refuses a slug already recorded.
- A search by a slug finds the entry carrying it and every entry linking to it, whatever their types.
- After a merge, a search by either slug finds every entry linking to either, including entries that sync in after the merge, and reading the old slug gives the entry kept.
- An entry of a type nothing in the plugin knows can be created, revised, found by type and by its own fields, and read.
- Every record already written reads as it did.
