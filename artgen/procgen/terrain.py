"""Procedural terrain (ground) tiles — v2.

Design goals from art review:
- warm, low-contrast surfaces (no eye-strain repetition, no garish accents);
- big soft patches + a fine texture layer + sparse soft details (grass sprigs,
  pebbles, rare pale flowers) so a single tile already looks non-uniform;
- many biomes: grass, forest_floor, pine_floor, dirt, sand, gravel, cobble,
  path, stone, snow, swamp, plus animated water.

Every layer wraps (details are plotted modulo tile), so tiles stay seamless
when repeated. Deterministic per seed; snapped to the canonical palette.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .. import TILE
from ..canvas import value_noise
from ..palette import hex_to_rgb, quantize

# ---- biome definitions -----------------------------------------------------
# shades: dark -> light, kept close together for low contrast.
# detail: counts per 32px tile (scaled by area for other sizes).

BIOMES: dict[str, dict] = {
    "grass": {
        "shades": ["#3e6631", "#446a32", "#4f7a3a", "#5f8f46"],
        "detail": {"sprig": 7, "flower": 1},
    },
    "forest_floor": {  # leafy / deciduous floor
        "shades": ["#345527", "#3e6631", "#446a32", "#4a7a3a"],
        "detail": {"sprig": 6, "leaf": 6},
    },
    "pine_floor": {  # coniferous — darker, needles
        "shades": ["#2f5a2b", "#345527", "#3e6631"],
        "detail": {"needle": 12},
    },
    "dirt": {
        "shades": ["#5a3a24", "#6e4a2f", "#7a5238", "#94684a"],
        "detail": {"pebble": 6, "crack": 3},
    },
    "sand": {
        "shades": ["#c4a86a", "#cbb08a", "#d9c07f", "#e3cf94"],
        "detail": {"pebble": 5, "speck": 8},
    },
    "path": {  # worn track surface for roads
        "shades": ["#94684a", "#c4a86a", "#cbb08a", "#d9c07f"],
        "detail": {"pebble": 5, "sprig": 1, "speck": 6},
    },
    "gravel": {  # crushed stone (щебёнка)
        "shades": ["#6e4a2f", "#7a7485", "#94684a", "#948da3"],
        "detail": {"pebble": 22},
    },
    "stone": {
        "shades": ["#565061", "#6a6475", "#7a7485", "#948da3"],
        "detail": {"crack": 5, "pebble": 4},
    },
    "snow": {
        "shades": ["#c8c8c0", "#e8e4dc", "#e8e8e0"],
        "detail": {"sparkle": 5, "blue": 4},
    },
    "swamp": {
        "shades": ["#3a2a1a", "#345527", "#446a32"],
        "detail": {"mud": 5, "slime": 3},
    },
}

# special-cased renderers
COBBLE = "cobble"
KINDS = tuple(BIOMES) + (COBBLE, "water")

# detail colours
_SPRIG_D, _SPRIG_L = "#3e6631", "#5f8f46"
_FLOWER = ["#e8e4dc", "#c9c2b5", "#d97b7b"]  # pale white / grey / soft pink (low-key)
_PEBBLE = ["#7a7485", "#948da3", "#94684a"]


def _plot(px, x, y, w, h, rgb):
    px[x % w, y % h] = (rgb[0], rgb[1], rgb[2], 255)


def _sprig(px, x, y, w, h, rgb):
    """Small V-shaped grass sprig (3 px), wrap-safe."""
    _plot(px, x, y, w, h, rgb)
    _plot(px, x - 1, y - 1, w, h, rgb)
    _plot(px, x + 1, y - 1, w, h, rgb)


def _needle(px, x, y, w, h, rgb):
    _plot(px, x, y, w, h, rgb)
    _plot(px, x, y - 1, w, h, rgb)


def _base_array(kind: str, w: int, h: int, seed: int) -> np.ndarray:
    """Base colour field over a w x h area: big soft patches + fine texture.

    Patch frequency scales with size so patches stay ~24px regardless of area —
    a single tile and a large baked field both look right, and patches flow
    continuously across a big field (no per-tile rhythm)."""
    shades = [hex_to_rgb(c) for c in BIOMES[kind]["shades"]]
    n = len(shades)
    pf = max(2, round(min(w, h) / 24))
    patches = value_noise(w, h, seed=seed, octaves=4, base_freq=pf, tileable=True)
    fine = value_noise(w, h, seed=seed + 101, octaves=2, base_freq=pf * 3, tileable=True)
    field = np.clip(patches * 0.82 + fine * 0.18, 0, 1)
    idx = np.clip((field * n).astype(int), 0, n - 1)
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = np.array(shades, np.uint8)[idx]
    return arr


def _scatter(im: Image.Image, kind: str, w: int, h: int, seed: int):
    """Sparse soft details on top of the base, all wrap-tileable."""
    spec = BIOMES[kind].get("detail", {})
    scale = (w * h) / (32 * 32)
    rng = np.random.default_rng(seed + 555)
    px = im.load()

    def n(key):
        return max(0, int(round(spec.get(key, 0) * scale)))

    def rx():
        return int(rng.integers(w))

    def ry():
        return int(rng.integers(h))

    for _ in range(n("sprig")):
        c = hex_to_rgb(_SPRIG_D if rng.random() < 0.6 else _SPRIG_L)
        _sprig(px, rx(), ry(), w, h, c)
    for _ in range(n("needle")):
        _needle(px, rx(), ry(), w, h, hex_to_rgb("#2f5a2b" if rng.random() < 0.5 else "#345527"))
    for _ in range(n("leaf")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb("#6e4a2f" if rng.random() < 0.5 else "#7a5238"))
    for _ in range(n("flower")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb(_FLOWER[int(rng.integers(len(_FLOWER)))]))
    for _ in range(n("pebble")):
        c = hex_to_rgb(_PEBBLE[int(rng.integers(len(_PEBBLE)))])
        x, y = rx(), ry()
        _plot(px, x, y, w, h, c)
        if rng.random() < 0.4:
            _plot(px, x + 1, y, w, h, c)
    for _ in range(n("crack")):
        x, y = rx(), ry()
        c = hex_to_rgb("#5a3a24" if kind != "stone" else "#565061")
        for k in range(int(rng.integers(2, 4))):
            _plot(px, x + k, y + (k % 2), w, h, c)
    for _ in range(n("speck")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb("#e3cf94"))
    for _ in range(n("sparkle")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb("#e8e8e0"))
    for _ in range(n("blue")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb("#948da3"))
    for _ in range(n("mud")):
        x, y = rx(), ry()
        for dx in (-1, 0, 1):
            _plot(px, x + dx, y, w, h, hex_to_rgb("#5a3a24"))
    for _ in range(n("slime")):
        _plot(px, rx(), ry(), w, h, hex_to_rgb("#5aa843"))


def _cobble(tile: int, seed: int) -> Image.Image:
    """Cobblestone road: rounded stones in a tileable brick layout."""
    rng = np.random.default_rng(seed)
    greys = ["#565061", "#6a6475", "#7a7485", "#948da3"]
    mortar = hex_to_rgb("#3a3a44")
    arr = np.zeros((tile, tile, 4), dtype=np.uint8)
    arr[..., :3] = mortar
    arr[..., 3] = 255
    im = Image.fromarray(arr, "RGBA")
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    sz = 6
    for row, gy in enumerate(range(0, tile, sz)):
        off = (sz // 2) if row % 2 else 0
        for gx in range(-sz, tile, sz):
            x = gx + off + 1
            c = hex_to_rgb(greys[int(rng.integers(len(greys)))])
            d.rounded_rectangle([x, gy + 1, x + sz - 2, gy + sz - 2], radius=2, fill=c + (255,))
            d.point((x + 1, gy + 2), fill=hex_to_rgb("#a8a8a0") + (255,))
    return quantize(im)


def ground(kind: str, tile: int = TILE, seed: int = 42) -> Image.Image:
    """One square ground tile for a biome. Deterministic, seamless when tiled."""
    if kind == COBBLE:
        return _cobble(tile, seed)
    if kind not in BIOMES:
        raise ValueError(f"unknown biome {kind!r}; choices: {sorted(KINDS)}")
    im = Image.fromarray(_base_array(kind, tile, tile, seed), "RGBA").copy()
    _scatter(im, kind, tile, tile, seed)
    return quantize(im)


def ground_rect(kind: str, w: int, h: int, seed: int = 42) -> Image.Image:
    """A large baked ground area (w x h). Soft patches flow continuously across
    the whole area (no per-tile rhythm) — for scene backgrounds / world chunks."""
    if kind == COBBLE:
        # tile the cobble pattern across the area
        base = _cobble(min(w, h, 64), seed)
        out = Image.new("RGBA", (w, h))
        tw, th = base.size
        for y in range(0, h, th):
            for x in range(0, w, tw):
                out.alpha_composite(base, (x, y))
        return out
    if kind not in BIOMES:
        raise ValueError(f"unknown biome {kind!r}; choices: {sorted(KINDS)}")
    im = Image.fromarray(_base_array(kind, w, h, seed), "RGBA").copy()
    _scatter(im, kind, w, h, seed)
    return quantize(im)


def water(frame: int = 0, tile: int = TILE, seed: int = 42) -> Image.Image:
    """Animated water frame: base blue, ripples, moving highlights."""
    base, ripple, hi = hex_to_rgb("#2f5e8f"), hex_to_rgb("#3f75ad"), hex_to_rgb("#7fa8cc")
    n = value_noise(tile, tile, seed=seed, octaves=2, base_freq=3, tileable=True)
    n = np.roll(n, frame * (tile // 3), axis=1)
    arr = np.empty((tile, tile, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = np.array(base, np.uint8)
    arr[n > 0.58, :3] = np.array(ripple, np.uint8)
    rng = np.random.default_rng(seed * 10 + frame)
    for _ in range(max(2, tile // 12)):
        y = int(rng.integers(0, tile))
        x = int(rng.integers(0, tile - 3))
        for dx in range(3):
            arr[y, (x + dx) % tile, :3] = np.array(hi, np.uint8)
    return quantize(Image.fromarray(arr, "RGBA"))


def variants(kind: str, tile: int = TILE, seed: int = 42, variety: int = 4) -> list[Image.Image]:
    if kind == "water":
        return [water(f, tile, seed) for f in range(max(1, variety))]
    return [ground(kind, tile, seed + i * 17) for i in range(max(1, variety))]


def generate(kinds=None, tile: int = TILE, seed: int = 42, variety: int = 4) -> dict[str, list[Image.Image]]:
    kinds = kinds or KINDS
    return {k: variants(k, tile, seed, variety) for k in kinds}
