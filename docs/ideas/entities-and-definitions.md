# Entities and definitions

Concerns the data format.

- **An `entity` type** carries `slug`, `kind`, and `aliases` in its `details`: the durable things entries are about, which entries name by slug.
- **A `resolve` tool** turns a name into a few candidate entities.
- **User-defined types** are `definition` records, following the same pattern as the built-in `journal` and `snapshot`.

Open: the name a user-defined type goes by in the tools: type, extension, or kind.
