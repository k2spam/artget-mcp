# Heroquarium ArtGen

Pixel-art asset pipeline for the game Heroquarium: procedural generation
(`procgen`), external-art normalization (`pixelize`), and an MCP server that
exposes both to Claude. See `ARTGEN_BLUEPRINT.md` for the full design.

**Canon:** generate at `TILE=32`, export downscaled to `16` for the current
renderer. All output snaps to the 53-colour palette in `palette.json` (single
source of truth). RGBA, binary alpha, light from top-left.

## Layout

```
palette.json          canonical palette (53 colours) — do not diverge
artgen/
  palette.py          load, redmean nearest-match, quantize, ramps
  canvas.py           pixel-map DSL, value noise, dither, shadow, outline, mirror
  pixelize.py         normalize any image/atlas -> palette + tile size
  procgen/            procedural generators (M2+)
mcp/                  MCP server (M5)
tools/                original game sources, kept for reference
tests/                palette + canvas acceptance tests
references/           style refs + Recraft prompts (for nngen / M7-M8)
out/                  generated art (gitignored)
```

## Setup

```bash
pip install -e '.[dev]'   # runtime + pytest
pytest -q                 # 14 tests
```

## pixelize

```bash
# single sprite -> 16x16 in palette
python -m artgen.pixelize in.png -o out/tree.png

# atlas: 4x4 grid, or 32px source tiles -> separate files
python -m artgen.pixelize sheet.png --grid 4 4 -o out/
python -m artgen.pixelize sheet.png --src-tile 32 -o out/
```

`--method box|lanczos` for "fat" (AI/painted) art, `nearest` for already-pixel art.

## procgen

```bash
python -m artgen.procgen terrain --tile 32 --seed 42 --variety 3 -o out/terrain/
python -m artgen.procgen nature  --tile 32 --seed 42 -o out/nature/
python -m artgen.procgen all -o out/
```

Terrain biomes: grass (+flowers), forest_floor, dirt, sand, stone, snow, swamp,
plus animated water frames — all tileable (seamless when repeated). Nature
props: round/pine/palm trees, bush, stump, boulder, small rock, flowers,
mushroom, grass tuft, reeds, skull. Each run writes PNGs + a `_*_sheet.png`
contact sheet.

## Status

- **M1 — done:** scaffold, palette, canvas primitives, pixelize ported.
- **M2 — done:** tileable terrain (7 biomes + water), 12 nature props, preview
  (contact sheets, 3x3 tiling check), procgen CLI. 20 tests green.
- M3+ — autotile transitions (core), buildings, MCP server, nngen (GPU). §11.
