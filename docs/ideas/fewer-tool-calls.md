# Fewer tool calls

Concerns the MCP server's tools.

Every tool call is a turn of the model, so a round trip costs far more than the lookup it makes. These were raised for the server and not built with it.

- **`search` takes names as well as slugs**, resolving each to its likely entities and searching by all of them, with each hit saying which name it came through, so a query needs no separate `resolve` call.
- **`write_journal` takes names instead of slugs**, writing when each name matches one entity and otherwise refusing with each name's candidates, so the common case is one call.