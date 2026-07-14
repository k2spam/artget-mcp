"""Canonical palette: single source of truth for all generated art.

Loads `palette.json` from the repo root. Provides hex<->rgb helpers, a fast
perceptual nearest-colour match (redmean), palette quantization, and colour
ramps for soft shading. Deterministic and dependency-light (no numpy needed).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Iterable

from PIL import Image

# Repo root = parent of this package dir.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE_JSON = os.path.join(_ROOT, "palette.json")

RGB = tuple[int, int, int]


def hex_to_rgb(h: str) -> RGB:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_to_hex(c: Iterable[int]) -> str:
    r, g, b = c
    return "#%02x%02x%02x" % (r, g, b)


def load(path: str = PALETTE_JSON) -> tuple[list[RGB], int]:
    """Return (colours as rgb tuples, source tile size)."""
    data = json.load(open(path, encoding="utf-8"))
    colors = [hex_to_rgb(c) for c in data["colors"]]
    return colors, int(data.get("tile", 16))


@lru_cache(maxsize=1)
def colors() -> tuple[RGB, ...]:
    """Cached palette colours (rgb tuples)."""
    return tuple(load()[0])


def hex_colors() -> list[str]:
    return [rgb_to_hex(c) for c in colors()]


def _redmean(a: RGB, b: RGB) -> int:
    """Cheap perceptual colour distance (redmean). Lower = closer."""
    r1, g1, b1 = a
    r2, g2, b2 = b
    rm = (r1 + r2) // 2
    dr, dg, db = r1 - r2, g1 - g2, b1 - b2
    return (((512 + rm) * dr * dr) >> 8) + 4 * dg * dg + (((767 - rm) * db * db) >> 8)


def nearest(px: RGB, palette: Iterable[RGB] | None = None) -> RGB:
    """Nearest palette colour to px by redmean distance. Deterministic."""
    pal = tuple(palette) if palette is not None else colors()
    best, bd = pal[0], 1 << 30
    for c in pal:
        d = _redmean(px, c)
        if d < bd:
            bd, best = d, c
    return best


def quantize(im: Image.Image, palette: Iterable[RGB] | None = None,
             alpha_cut: int = 128, cache: dict | None = None) -> Image.Image:
    """Snap an RGBA image exactly to the palette; alpha becomes binary."""
    pal = tuple(palette) if palette is not None else colors()
    im = im.convert("RGBA")
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    src, dst = im.load(), out.load()
    cache = {} if cache is None else cache
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a < alpha_cut:
                continue
            key = (r, g, b)
            c = cache.get(key)
            if c is None:
                c = cache[key] = nearest(key, pal)
            dst[x, y] = (c[0], c[1], c[2], 255)
    return out


def ramp(c0: RGB, c1: RGB, n: int) -> list[RGB]:
    """Linear colour ramp from c0 to c1 with n steps (inclusive)."""
    if n <= 1:
        return [c0]
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(tuple(round(a + (b - a) * t) for a, b in zip(c0, c1)))  # type: ignore
    return out


def colors_outside(im: Image.Image, palette: Iterable[RGB] | None = None,
                   alpha_cut: int = 128) -> set[RGB]:
    """Set of opaque colours in im that are NOT in the palette (for tests)."""
    pal = set(palette) if palette is not None else set(colors())
    im = im.convert("RGBA")
    bad = set()
    for (r, g, b, a) in im.getdata():
        if a >= alpha_cut and (r, g, b) not in pal:
            bad.add((r, g, b))
    return bad
