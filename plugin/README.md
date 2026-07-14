# Heroquarium ArtGen plugin

Isometric pixel-art generation for Heroquarium, exposed as MCP tools, with a
bundled usage skill.

## Contents

- `.claude-plugin/plugin.json` — manifest (name, version).
- `.mcp.json` — starts the `heroquarium-artgen` stdio MCP server.
- `mcp/server.py` — the server (tools: terrain, water, coast, house, prop, tree,
  actor, actor_walk, anim, list_palette, list_roster).
- `skills/heroquarium-artgen/SKILL.md` — how a session should use the tools.
- `artgen/`, `palette.json` — the generation library the server imports.

## Requirements

The host Python must have `pillow`, `numpy`, and `mcp` installed:

```bash
pip install pillow numpy mcp
```

## Install

Save the `.plugin` file from the build folder and install it via the Cowork
app, or register the server directly:

```bash
claude mcp add heroquarium-artgen -- python3 /abs/path/to/plugin/mcp/server.py
```

Built artifacts live in the repo's `build/` folder, one versioned `.plugin`
per build (see `build/BUILDS.md`).
