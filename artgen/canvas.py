"""Low-level pixel primitives for procedural generation.

All helpers work on RGBA PIL images and are deterministic given a seed.
Ported and generalized from the game's `gen_assets.py` (pixel-maps + noise),
parameterized by tile size. Light source is top-left by convention.
"""
from __future__ import annotations

import random
from typing import Mapping, Sequence

import numpy as np
from PIL import Image

from . import TILE
from .palette import RGB, hex_to_rgb, nearest, quantize, ramp  # re-export ramp

__all__ = [
    "img", "as_rgba", "from_map", "ramp", "value_noise", "dither",
    "drop_shadow", "outline", "mirror_x", "snap_palette",
]


def img(tile: int = TILE) -> Image.Image:
    """Empty transparent RGBA tile."""
    return Image.new("RGBA", (tile, tile), (0, 0, 0, 0))


def as_rgba(c, a: int = 255) -> tuple[int, int, int, int]:
    """Accept a hex string or rgb(a) tuple -> rgba tuple."""
    if isinstance(c, str):
        r, g, b = hex_to_rgb(c)
        return (r, g, b, a)
    if len(c) == 4:
        return tuple(c)  # type: ignore
    r, g, b = c
    return (r, g, b, a)


def from_map(rows: Sequence[str], pal: Mapping[str, object]) -> Image.Image:
    """Build a tile from a pixel-map: rows of chars -> palette colours.

    Grid must be square (len(rows) == len(each row)). '.' and any char mapping
    to None are transparent. Values may be hex strings or rgb(a) tuples.
    """
    n = len(rows)
    im = img(n)
    px = im.load()
    for y, row in enumerate(rows):
        if len(row) != n:
            raise ValueError(f"row {y} len={len(row)} != {n}: {row!r}")
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            c = pal.get(ch)
            if c is None:
                continue
            px[x, y] = as_rgba(c)
    return im


def value_noise(w: int, h: int, seed: int = 0, octaves: int = 3,
                base_freq: int = 2) -> np.ndarray:
    """Coherent value noise in [0,1], shape (h, w). Deterministic per seed.

    Sums `octaves` layers of bilinearly-upsampled random grids at doubling
    frequency and halving amplitude (fractal / fBm).
    """
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float64)
    amp, amp_sum = 1.0, 0.0
    freq = base_freq
    for _ in range(octaves):
        gh, gw = freq + 1, freq + 1
        grid = rng.random((gh, gw))
        layer = np.asarray(
            Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR),
            dtype=np.float64,
        ) / 255.0
        acc += layer * amp
        amp_sum += amp
        amp *= 0.5
        freq *= 2
    return acc / amp_sum


# Ordered (Bayer) dither matrices, normalized to (0,1).
_BAYER2 = np.array([[0, 2], [3, 1]], dtype=np.float64) / 4.0
_BAYER4 = np.array([
    [0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5],
], dtype=np.float64) / 16.0


def dither(a, b, mask: np.ndarray, pattern: str = "bayer4") -> Image.Image:
    """Ordered dither between colours a and b using a threshold `mask` in [0,1].

    Where mask > bayer threshold -> colour b, else colour a. `mask` shape sets
    the output size. Returns opaque RGBA.
    """
    a, b = as_rgba(a), as_rgba(b)
    h, w = mask.shape
    m = _BAYER2 if pattern == "bayer2" else _BAYER4
    tile = np.tile(m, (h // m.shape[0] + 1, w // m.shape[1] + 1))[:h, :w]
    pick_b = mask > tile
    arr = np.empty((h, w, 4), dtype=np.uint8)
    arr[..., :] = a
    arr[pick_b] = b
    return Image.fromarray(arr, "RGBA")


def mirror_x(sprite: Image.Image) -> Image.Image:
    """Left half mirrored onto the right for perfect horizontal symmetry."""
    sprite = sprite.convert("RGBA")
    w, h = sprite.size
    left = sprite.crop((0, 0, (w + 1) // 2, h))
    out = sprite.copy()
    out.paste(left.transpose(Image.FLIP_LEFT_RIGHT), (w // 2, 0))
    out.paste(left, (0, 0))
    return out


def outline(sprite: Image.Image, color, alpha_cut: int = 128) -> Image.Image:
    """Add a 1px outline in `color` around the sprite's alpha silhouette."""
    sprite = sprite.convert("RGBA")
    w, h = sprite.size
    src = sprite.load()
    out = sprite.copy()
    dst = out.load()
    oc = as_rgba(color)
    for y in range(h):
        for x in range(w):
            if src[x, y][3] >= alpha_cut:
                continue
            # transparent pixel adjacent to an opaque one -> outline
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] >= alpha_cut:
                    dst[x, y] = oc
                    break
    return out


def drop_shadow(sprite: Image.Image, dx: int = 1, dy: int = 1,
                color=(0, 0, 0), alpha: int = 90,
                alpha_cut: int = 128) -> Image.Image:
    """Composite a soft offset shadow of the sprite's silhouette beneath it."""
    sprite = sprite.convert("RGBA")
    w, h = sprite.size
    r, g, b = color[:3]
    # silhouette -> shadow colour with given alpha
    sil = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sp, silp = sprite.load(), sil.load()
    for y in range(h):
        for x in range(w):
            if sp[x, y][3] >= alpha_cut:
                silp[x, y] = (r, g, b, alpha)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(sil, (dx, dy))
    canvas.alpha_composite(sprite, (0, 0))
    return canvas


def snap_palette(sprite: Image.Image, palette=None, alpha_cut: int = 128) -> Image.Image:
    """Final quantization to the canonical palette (thin wrapper)."""
    return quantize(sprite, palette, alpha_cut)
