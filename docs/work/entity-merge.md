# Entity merge

Promoted from the idea Entity audit.

Two entities sometimes turn out to be one, such as `meds` recorded beside `medication`. Merging records that once, and from then on the Brain treats the two slugs as one entity under a canonical slug: an entity can be known by more than one slug.

## Decided

- **A merge is one record, not a revision of every entry.** A duplicate that is widespread would otherwise write a revision for every entry naming it, a storm of writes for one fact. That two slugs are one entity is a fact about the entity, so it is recorded once, against the entity.
- **The local index applies merges when it builds.** An entry naming the old slug counts as naming the canonical one, so a search by either slug finds every entry about the entity. Entries that name the old slug and sync in after the merge are covered the same way, with nothing more to write.
- **Deciding that two entities are one is judgment.** The model decides; the index only applies what was recorded.

## Suggested

- A listing of the entities in use, with how many entries name each, for spotting duplicates and for a query that starts by surveying the subjects.
- An audit pass, a dreaming pass, that looks through the entities for duplicates and proposes merges.
- A new write naming a merged-away slug is refused, and the refusal names the canonical slug.

## Done when

- One call merges an entity into another, writing one record and revising no entries.
- A search by either slug finds every entry naming either, including entries that sync in after the merge.
- `resolve` and `read` give the canonical entity for the old slug.
