# Isometric integration spec (Heroquarium)

How the iso art from `artgen/iso.py` maps into the game renderer. This is the
contract between the asset pipeline and the engine; the pipeline emits sprites +
manifests, the engine places and animates them.

## 1. Projection

2:1 dimetric. World axes: **x** east (screen down-right), **y** south
(screen down-left), **z** up. One ground tile is a `64 x 32` diamond.

```
HW = 32   # half tile width
HH = 16   # half tile height
ZS = 20   # screen pixels per world z-unit

screen_x = (x - y) * HW
screen_y = (x + y) * HH - z * ZS
```

Inverse (for a point on the ground, z = 0), used for mouse picking:

```
x = (screen_x / HW + screen_y / HH) / 2
y = (screen_y / HH - screen_x / HW) / 2
tile = (floor(x), floor(y))
```

A world origin offset `(OX, OY)` is added when blitting (camera pan = change
`OX,OY`). There is **no camera rotation** (fixed like Fallout 1-2).

## 2. Ground: diamonds, biomes, coasts

- Each ground cell is a diamond sprite (`iso.diamond(kind, seed, world=(i,j))`).
  Mottling is sampled from a global world-space noise field so patches flow
  across cells (no per-tile rhythm).
- Biome borders are softened with a vegetation `fringe` on edges facing a
  grassier neighbour.
- **Water/coast**: a cell whose four grid-corners mix land/water renders with
  `iso.coast_tile(corners, ...)`, where `corners = (top, right, bottom, left)`
  booleans for the four diamond vertices. The waterline is a bilinear corner
  field + edge-vanishing noise, so it is an organic curve **and** seamless with
  neighbours (shared corners → identical edges). Foam runs along the waterline.
  The engine feeds `corners` from its per-corner water mask (dual-grid).

## 3. Objects: anchors + depth sort

- Every object sprite carries an **anchor** `(ax, ay)` = the pixel of its world
  origin `(wx, wy, 0)`. Blit at `(OX + screen_x - ax, OY + screen_y - ay)`.
- **Painter's order**: draw ground first (never occludes objects), then objects
  sorted ascending by depth `key = (wx + wy)`. For multi-tile objects use the
  **front-most footprint corner** `(wx + fx) + (wy + fy)`. Break ties by base z
  (shorter/ground props before tall ones). Taller objects (houses, trees) never
  need to split because the fixed camera + front-corner key resolves overlaps
  for convex footprints; very large footprints should be split into per-tile
  slices if artifacts appear.

## 4. Picking & collision

- Screen→tile via the inverse projection (§1). For objects taller than one
  tile, hit-test the footprint rectangle, not the sprite bounds.
- Collision/movement runs on the tile grid (unchanged from top-down); only the
  render mapping differs.

## 5. Assets & animation (hybrid model)

- **Baked frame animations** ship as horizontal sprite sheets + a manifest
  (`out/iso_anim/manifest.json`): `smoke`, `campfire`, `glow` (window/lamp
  light), `water`. Each entry: `{sheet, frames, frame_w, frame_h, fps, loop}`.
  The engine plays them on a timer; smoke/light are attached only to some
  buildings (data-driven, not every chimney).
- **Engine-side motion (shader)**: grass and tree-canopy **sway** and subtle
  extra water shimmer are a vertex/UV wobble applied to static sprites at
  runtime — not baked — to keep atlases small and motion smooth.
- All sprites are RGBA, palette-snapped (`palette.json`), binary alpha,
  top-left light.

## 6. Renderer refactor checklist (game side)

1. Replace the square tile blit with the diamond projection (§1) and per-cell
   ground draw incl. `coast_tile` for shorelines.
2. Add a depth-sorted object pass (§3) keyed by footprint front corner.
3. Convert input picking to the inverse projection (§4).
4. Load the anim manifest; drive `smoke/campfire/glow/water` on a clock; add the
   sway shader for grass/foliage.
5. Camera = `(OX, OY)` pan; cull off-screen cells; chunk the map for large
   worlds (render visible chunks only).

## 7. Status

Prototype lives in `artgen/iso.py` (+ `scripts/iso_*.py`). Terrain, biomes,
organic lakes, flora, houses (log→stone, 1–2 storeys), fenced yards, roads,
baked anims, and a world composer (`scripts/iso_world.py`) are done. Remaining
before shipping: promote the composer to a reusable module, export atlases +
manifests for the whole set, then the game-side refactor above.
