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
python -m artgen.procgen terrain  --tile 32 --seed 42 --variety 3 -o out/terrain/
python -m artgen.procgen nature   --tile 32 --seed 42 -o out/nature/
python -m artgen.procgen autotile --from grass --to water -o out/edges/
python -m artgen.procgen building --size L --roof red --walls stone -o out/
python -m artgen.procgen village -o out/village/
python -m artgen.procgen all -o out/
```

Buildings: parametric houses (size S/M/L x roof slate/red/thatch x walls stone/
timber/frame) plus a prop kit — fence, gate, well, barrel, crate, signpost,
lantern, market stall, woodpile, haystack. `village` writes the whole catalog +
a gallery sheet.

Terrain biomes: grass (+flowers), forest_floor, dirt, sand, stone, snow, swamp,
plus animated water frames — all tileable (seamless when repeated). Nature
props: round/pine/palm trees, bush, stump, boulder, small rock, flowers,
mushroom, grass tuft, reeds, skull. Each run writes PNGs + a `_*_sheet.png`
contact sheet.

## Status

- **M1 — done:** scaffold, palette, canvas primitives, pixelize ported.
- **M2 — done:** tileable terrain (7 biomes + water), 12 nature props, preview
  (contact sheets, 3x3 tiling check), procgen CLI.
- **M3 — done:** corner-based 16-tile autotile transitions between any two
  biomes, organic edges, dark rim, animated water foam. Seams exact by
  construction (bilinear corner field + edge-vanishing noise). Emits a bitmask
  manifest for the game renderer. 28 tests green.
- **M4 — done:** parametric buildings (3x3x3 house combos: size x roof x walls)
  + 10-piece prop kit (fence/gate/well/barrel/crate/signpost/lantern/stall/
  woodpile/haystack), gallery preview, village catalog. 35 tests green.
- **M1-M4 polish pass — done:** warm low-contrast terrain with soft details
  (sprigs/pebbles/rare pale flowers) + new biomes (pine_floor, gravel, cobble,
  dirt, path) and 6+ variants each to kill repetition; roads/paths as a linear
  autotile feature (`roads.py`, layouts cross/curve/plaza…) with grassy fringe;
  reference-level detailed houses (varied shingles, ridge cap, moss, 4-pane
  windows w/ muntins+shutters+glow, timber framing, stone base, framed door,
  capped chimney) + decor kit (bucket, sack, potted plant, flower box, lantern,
  axe-stump, …). Demo: `python scripts/demo_scene.py`. 40 tests green.
- **Anti-repetition pass — done:** autotile tiles take a position-hashed
  `variant` that reseeds interior noise + fill (seams stay exact because noise
  vanishes at edges), so roads/maps no longer show a repeating pattern;
  `terrain.ground_rect()` bakes a large continuous ground field (soft patches
  flow across the whole area, no per-tile rhythm) for scene/chunk backgrounds;
  softer terrain details + more nature (flat rock, fallen branch, mushroom
  cluster).
- M5+ — MCP server, export/integration, nngen (GPU). §11.

### Autotile scheme

Corner 4-bit Wang / dual-grid: each tile's four corners (NW=1, NE=2, SE=4,
SW=8) mark upper vs lower terrain, giving 16 tiles. The boundary along any edge
is a pure function of that edge's two shared corners, so tiles that abut on the
dual grid are exactly seamless (0-mismatch, verified in tests). The renderer
picks a tile per world corner-cell from its 2x2 terrain values; the mapping is
written to `<from>_<to>.manifest.json`.
