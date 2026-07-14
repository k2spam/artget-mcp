---
name: heroquarium-artgen
description: >
  Generate isometric pixel-art assets for the Heroquarium game — terrain
  biomes, organic lake shorelines, houses (log→stone, 1–2 storeys), decor/props,
  trees, and animated actors (villagers/animals/enemies) with full 4-direction
  walk cycles, plus baked effect animations (smoke/campfire/window-glow/water).
  Use whenever a session needs game sprites, tiles, a character/creature, a
  walk-animation set, or a composed world patch for Heroquarium.
---

# Heroquarium ArtGen (isometric) — usage skill

This plugin wraps the `artgen` isometric pipeline as MCP tools. Everything is
**deterministic per seed**, snapped to the game's 53-colour palette, RGBA with
binary alpha, lit from the top-left. Each tool writes PNG(s) under `out/mcp/`
and returns their `paths` plus a base64 `preview_png_b64` — always show the
preview to the user.

## Core conventions (read before generating)

- **Projection**: 2:1 dimetric. A ground cell is a 64×32 diamond.
  `screen_x=(x−y)·32`, `screen_y=(x+y)·16 − z·20`. Fixed camera (no rotation).
- **Anchor**: object tools return `anchor=[ax,ay]` = the pixel of the object's
  world origin (its feet / footprint NW corner). The engine blits at
  `(OX+screen_x−ax, OY+screen_y−ay)`.
- **Directions** (actors): `S` toward viewer, `N` away, `E` right, `W` left.
  Movement uses these four; W is the mirror of E.
- **Animation is hybrid**: discrete motion (smoke, campfire, window/lamp glow,
  water, walk cycles) is delivered as **baked sprite sheets + a JSON manifest**
  (`frames`, `fps`, `loop`, `frame_w/h`). Grass/tree **sway** is expected to be
  a runtime engine shader — do NOT try to bake it.
- **Randomisation**: change `seed` to get a different villager (clothes/hair/
  hat/face), a different tree, a different mottling — same seed always
  reproduces the same sprite.

## Tools

- `list_palette()` → palette hexes + projection constants. Call once if you need
  colours or to explain the projection.
- `list_roster()` → valid `actors`, `directions`, `biomes`, `wall_materials`,
  `roof_types`, `tree_species`, `conifer_species`. **Call this first** when
  unsure which names are valid; pass only listed values.
- `iso_terrain(kind, seed)` → one ground diamond. `kind` ∈ grass, meadow,
  forest_floor, sand, dirt, stone, snow, path.
- `iso_water(frame, seed)` → an animated water diamond (one `frame`).
- `iso_coast(corners, seed, land_kind)` → an **organic shoreline** diamond.
  `corners=(top,right,bottom,left)`, 1=water. Mixed corners give a curved
  waterline with foam; all-0 = land, all-1 = open water. Feed corners from a
  per-corner water mask so lakes get non-rectangular edges.
- `iso_house(walls, roof, storeys, seed, smoke)` → a house. `walls` ∈ log,
  timber, plaster, stone; `roof` ∈ red, slate, thatch, wood; `storeys` 1–2;
  `smoke` toggles the chimney plume (leave off for some houses).
- `iso_prop(name, seed)` → decor/structure: well, fence, gate, barrel, crate,
  bench, mailbox, lamp_post, firewood, garden_bed, campfire, boat, reeds,
  lily_pads, bush, rock, flowers, stump, log.
- `iso_tree(species, seed, conifer)` → a tree. deciduous species oak/maple/
  birch/poplar/linden; set `conifer=true` for spruce/pine/fir.
- `iso_actor(name, direction, frame, seed)` → one actor still-frame. Good for a
  quick look; for movement use `iso_actor_walk`.
- `iso_actor_walk(name, seed)` → the **full walk set**: 4 directions × 4 frames
  as sprite sheets + a `manifest.json`. This is what the game consumes for a
  walking character/creature.
- `iso_anim(effect, seed, nframes)` → a baked effect sheet + manifest. `effect`
  ∈ smoke, campfire, glow, water.

Actors (`iso_actor`/`iso_actor_walk`): villager, trader, skeleton, goblin,
rabbit, deer, wolf, fox, boar, bear, sheep, cow, slime, chicken, bat.

## Example session flows

- *"Make me a couple of random villagers walking."* → `list_roster()` →
  `iso_actor_walk("villager", seed=1)`, `iso_actor_walk("villager", seed=2)`;
  show the E-direction preview, tell the user the sheets + manifest paths.
- *"A stone two-storey house with smoke."* →
  `iso_house("stone","slate",storeys=2,seed=3,smoke=true)`; show preview.
- *"A lake with soft edges."* → generate the shoreline ring with `iso_coast`
  for the mixed-corner cells and `iso_water` for interior cells; explain the
  engine feeds `corners` per cell.
- *"A campfire animation."* → `iso_anim("campfire", seed=1)`; hand over the
  sheet + manifest (fps/loop) for the engine.

## Notes

- Always surface `preview_png_b64` to the user and report the saved `paths`.
- Prefer `iso_actor_walk` / `iso_anim` (sheets + manifest) when the user wants
  something that moves; use single-frame tools only for stills.
- Full projection / depth-sort / picking / renderer refactor details live in
  `docs/iso_integration.md`.
