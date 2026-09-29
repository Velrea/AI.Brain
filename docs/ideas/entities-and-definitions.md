# Entities and definitions

Concerns [the data format](../architecture/data-format.md).

- **An `entity` type** extends `journal-entry` with `slug`, `kind`, and `aliases`: the durable things entries are about, which `entities` names by slug.
- **A `resolve` tool** turns a name into a few candidate entities.
- **User-defined types** are `definition` records, following the same pattern as the built-in `journal-entry` and `snapshot`.

Open: the name a user-defined type goes by in the tools: type, extension, or kind.
