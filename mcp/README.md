# Heroquarium ArtGen — MCP server

Exposes the isometric generators (terrain, coasts, houses, props, trees,
actors, walk sets, effect animations) as MCP tools over stdio. Each tool writes
PNG(s) to `out/mcp/` and returns their paths + a base64 preview.

## Install

```bash
pip install -e '.[mcp]'      # installs the `mcp` package (FastMCP)
```

## Register with Claude

Local stdio server:

```bash
claude mcp add heroquarium-artgen -- python /abs/path/to/ArtGen-MCP/mcp/server.py
```

After that the tools appear as `mcp__heroquarium-artgen__*` in a session. The
usage guide for sessions is `skills/heroquarium-artgen/SKILL.md`.

## Tools

`list_palette`, `list_roster`, `iso_terrain`, `iso_water`, `iso_coast`,
`iso_house`, `iso_prop`, `iso_tree`, `iso_actor`, `iso_actor_walk`, `iso_anim`.

Each returns `{paths, preview_png_b64, ...}`. `iso_actor_walk` and `iso_anim`
also return an animation `manifest` (frames, fps, loop, directions).

The tool bodies are plain `gen_*` functions in `server.py` (usable/testable
without the `mcp` package installed); the `@app.tool()` wrappers just call them.
