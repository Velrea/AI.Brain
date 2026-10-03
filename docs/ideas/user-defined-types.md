# User-defined types

Concerns the data format and writing.

- **User-defined types** are `definition` records, following the same pattern as the built-in `journal`, `entity`, and `snapshot`.
- **Skills are the extension point.** The core module guards the files, the MCP server carries the rules, and skills carry the judgment and context. A skill of someone else's, such as one for research, can be built on the Brain's storage model: as long as it records through the same concepts (journal entries, entities, their types and details), its data reads back with everything else. A skill that needs data of its own shape could bring its own type.

Open: the name a user-defined type goes by in the tools: type, extension, or kind.
