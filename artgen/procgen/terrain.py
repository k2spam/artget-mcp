"""Procedural terrain (ground) tiles.

Each biome is a base colour plus two shades applied by *tileable* value noise,
so a tile repeats seamlessly across the map (edge-to-edge continuity). Variety
comes purely from the seed; one seed -> one tile, always. Water returns an
animated set of ripple frames.

All output is snapped to the canonical palette and has full (opaque) alpha —
ground has no outline by convention.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .. import TILE
from ..canvas import value_noise
from ..palette import RGB, hex_to_rgb, quantize

# biome -> (base, dark, light). Colours are palette hexes (see palette.json).
BIOMES: dict[str, tuple[str, str, str]] = {
    "grass":        ("#4f7a3a", "#446a32", "#5f8f46"),
    "forest_floor": ("#3e6631", "#345527", "#4a7a3a"),
    "dirt":         ("#6e4a2f", "#5a3a24", "#7a5238"),
    "sand":         ("#d9c07f", "#c4a86a", "#e3cf94"),
    "stone":        ("#6a6475", "#565061", "#7a7485"),
    "snow":         ("#e8e8e0", "#c8c8c0", "#e8e4dc"),
    "swamp":        ("#446a32", "#3a2a1a", "#5a3a24"),
}

KINDS = tuple(BIOMES) + ("water",)


def _mottled(base: RGB, dark: RGB, light: RGB, tile: int, seed: int,
             low: float = 0.42, high: float = 0.66) -> Image.Image:
    """Three-tone ground: base, with dark/light patches driven by tileable noise."""
    n = value_noise(tile, tile, seed=seed, octaves=4, base_freq=4, tileable=True)
    arr = np.empty((tile, tile, 4), dtype=np.uint8)
    arr[..., 3] = 255
    b = np.array(base, np.uint8)
    d = np.array(dark, np.uint8)
    l = np.array(light, np.uint8)
    arr[..., :3] = b
    arr[n < low, :3] = d
    arr[n > high, :3] = l
    return Image.fromarray(arr, "RGBA")


def ground(kind: str, tile: int = TILE, seed: int = 42) -> Image.Image:
    """One ground tile for a biome, snapped to the palette. Deterministic."""
    if kind not in BIOMES:
        raise ValueError(f"unknown biome {kind!r}; choices: {sorted(BIOMES)}")
    base, dark, light = (hex_to_rgb(c) for c in BIOMES[kind])
    im = _mottled(base, dark, light, tile, seed)
    if kind == "grass":
        im = _scatter_flowers(im, seed)
    return quantize(im)


def _scatter_flowers(im: Image.Image, seed: int, n: int = 5) -> Image.Image:
    """Sprinkle a few flower/pebble accent pixels on grass (deterministic)."""
    rng = np.random.default_rng(seed + 7)
    tile = im.size[0]
    im = im.copy()
    px = im.load()
    accents = [(227, 208, 90), (217, 123, 123), (232, 228, 220)]  # e3d05a d97b7b e8e4dc
    for _ in range(n):
        x, y = int(rng.integers(2, tile - 2)), int(rng.integers(2, tile - 2))
        c = accents[int(rng.integers(len(accents)))]
        px[x, y] = (c[0], c[1], c[2], 255)
    return im


def water(frame: int = 0, tile: int = TILE, seed: int = 42) -> Image.Image:
    """One animation frame of water: base blue, ripples, moving highlights."""
    base, ripple, hi = hex_to_rgb("#2f5e8f"), hex_to_rgb("#3f75ad"), hex_to_rgb("#7fa8cc")
    # phase-shifted tileable noise gives the illusion of motion between frames
    n = value_noise(tile, tile, seed=seed, octaves=2, base_freq=3, tileable=True)
    shift = frame * (tile // 3)
    n = np.roll(n, shift, axis=1)
    arr = np.empty((tile, tile, 4), dtype=np.uint8)
    arr[..., 3] = 255
    arr[..., :3] = np.array(base, np.uint8)
    arr[n > 0.55, :3] = np.array(ripple, np.uint8)
    # short horizontal highlight dashes where noise peaks
    rng = np.random.default_rng(seed * 10 + frame)
    for _ in range(max(2, tile // 12)):
        y = int(rng.integers(0, tile))
        x = int(rng.integers(0, tile - 3))
        for dx in range(3):
            arr[y, (x + dx) % tile, :3] = np.array(hi, np.uint8)
    return quantize(Image.fromarray(arr, "RGBA"))


def variants(kind: str, tile: int = TILE, seed: int = 42, variety: int = 3) -> list[Image.Image]:
    """`variety` distinct tiles for a biome (or ripple frames for water)."""
    if kind == "water":
        return [water(f, tile, seed) for f in range(max(1, variety))]
    return [ground(kind, tile, seed + i) for i in range(max(1, variety))]


def generate(kinds=None, tile: int = TILE, seed: int = 42, variety: int = 3) -> dict[str, list[Image.Image]]:
    """All terrain tiles keyed by biome. `kinds` limits the set if given."""
    kinds = kinds or KINDS
    return {k: variants(k, tile, seed, variety) for k in kinds}
