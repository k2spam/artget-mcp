"""Autotile transitions between two biomes (the core of the pipeline).

Model: **corner-based 4-bit Wang** (a.k.a. dual-grid blob). Each tile is defined
by whether each of its four corners is the *upper* terrain:

    bit  NW=1  NE=2  SE=4  SW=8      -> 16 tiles, index 0..15

The upper/lower boundary inside a tile is a bilinear field over the four corner
values, thresholded at 0.5, with tileable noise added only in the interior (the
noise is windowed to vanish at all four edges). Consequence: **the boundary
along any edge is a pure function of that edge's two shared corners**, so two
tiles that legally abut on the dual grid have identical mask columns/rows on the
seam — exactly seamless by construction (0 mismatch; see tests).

The renderer picks a tile per world corner-cell from its 2x2 corner terrain
values; `corner_index()` documents the mapping (mirrored into the manifest).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .. import TILE
from ..canvas import value_noise
from ..palette import hex_to_rgb, quantize
from . import terrain

# corner bit flags
NW, NE, SE, SW = 1, 2, 4, 8
_CORNER_BITS = (NW, NE, SE, SW)  # order used everywhere: (nw, ne, se, sw)

# foam colours (water side of shoreline)
_FOAM = ("#7fa8cc", "#e8e8e0")


def corner_index(nw: int, ne: int, se: int, sw: int) -> int:
    """Bitmask index for a corner configuration (1=upper terrain)."""
    return (NW if nw else 0) | (NE if ne else 0) | (SE if se else 0) | (SW if sw else 0)


def index_corners(idx: int) -> tuple[int, int, int, int]:
    """Inverse of corner_index: (nw, ne, se, sw) booleans (as 0/1)."""
    return tuple(1 if idx & b else 0 for b in _CORNER_BITS)  # type: ignore


def corner_field(tile: int, corners, seed: int = 42, rough: float = 0.30) -> np.ndarray:
    """Bilinear corner field in [~0,1] with edge-vanishing interior noise.

    corners = (nw, ne, se, sw). Noise is multiplied by sin(pi*u)*sin(pi*v) so it
    is exactly zero on every edge -> edges depend only on the shared corners.
    """
    nw, ne, se, sw = (float(c) for c in corners)
    u = np.linspace(0.0, 1.0, tile)[None, :]
    v = np.linspace(0.0, 1.0, tile)[:, None]
    top = nw * (1 - u) + ne * u
    bot = sw * (1 - u) + se * u
    f = top * (1 - v) + bot * v
    if rough > 0:
        window = np.sin(np.pi * u) * np.sin(np.pi * v)
        n = value_noise(tile, tile, seed=seed, octaves=3, base_freq=3, tileable=True)
        f = f + (n - 0.5) * 2.0 * rough * window
    return f


def _mask(tile, corners, seed, rough) -> np.ndarray:
    return corner_field(tile, corners, seed, rough) >= 0.5


def _terrain_rgb(kind: str, tile: int, seed: int, frame: int = 0) -> np.ndarray:
    """RGB array (tile,tile,3) of a biome tile (water is animated)."""
    im = terrain.water(frame, tile, seed) if kind == "water" else terrain.ground(kind, tile, seed)
    return np.asarray(im.convert("RGB"), dtype=np.uint8)


def _boundary(mask: np.ndarray) -> np.ndarray:
    """Upper-side pixels touching a lower-side 4-neighbour (the inner rim)."""
    lower = ~mask
    touch = np.zeros_like(mask)
    touch[:-1, :] |= lower[1:, :]
    touch[1:, :] |= lower[:-1, :]
    touch[:, :-1] |= lower[:, 1:]
    touch[:, 1:] |= lower[:, :-1]
    return mask & touch


def _water_edge(mask: np.ndarray) -> np.ndarray:
    """Lower-side (water) pixels touching the upper terrain — where foam sits."""
    upper = mask
    touch = np.zeros_like(mask)
    touch[:-1, :] |= upper[1:, :]
    touch[1:, :] |= upper[:-1, :]
    touch[:, :-1] |= upper[:, 1:]
    touch[:, 1:] |= upper[:, :-1]
    return (~mask) & touch


def transition(upper: str, lower: str, corners, tile: int = TILE,
               seed: int = 42, frame: int = 0, rim: bool = True,
               foam: bool = True, variant: int = 0) -> Image.Image:
    """One transition tile: `upper` biome intruding over `lower` per corners.

    `variant` reseeds the *interior* mask noise and the fill textures so that
    repeated tiles don't look identical. Because the corner-field noise is
    windowed to vanish at every edge, seams stay exact regardless of variant
    (edges depend only on the shared corners) — verified in tests."""
    vseed = seed + variant * 7919
    mask = _mask(tile, corners, vseed, rough=0.30)
    up = _terrain_rgb(upper, tile, vseed)
    lo = _terrain_rgb(lower, tile, vseed, frame)
    out = np.where(mask[..., None], up, lo)

    if rim and upper in terrain.BIOMES:
        rim_col = np.array(hex_to_rgb(terrain.BIOMES[upper]["shades"][0]), np.uint8)  # darkest shade
        out[_boundary(mask)] = rim_col

    if foam and lower == "water":
        edge = _water_edge(mask)
        # animate: alternate foam colour and thin/thick band per frame
        f0 = np.array(hex_to_rgb(_FOAM[0]), np.uint8)
        f1 = np.array(hex_to_rgb(_FOAM[1]), np.uint8)
        out[edge] = f1 if frame % 2 else f0
        # a fainter second ripple line just outside the first (frame-dependent)
        edge2 = _water_edge(mask | np.roll(edge, 1, axis=0)) & ~edge & ~mask
        if frame % 2 == 0:
            out[edge2] = f0

    rgba = np.dstack([out, np.full(out.shape[:2], 255, np.uint8)])
    return quantize(Image.fromarray(rgba, "RGBA"))


def generate(upper: str, lower: str, tile: int = TILE, seed: int = 42,
             frame: int = 0) -> dict[int, Image.Image]:
    """All 16 corner-indexed transition tiles for an upper/lower pair."""
    return {idx: transition(upper, lower, index_corners(idx), tile, seed, frame)
            for idx in range(16)}


def _variant(r: int, c: int, seed: int, pool: int) -> int:
    """Deterministic position-hashed variant index in [0, pool)."""
    return int((r * 928371 + c * 1237 + seed * 13) % pool)


def render_from_grid(upper: str, lower: str, grid: np.ndarray, tile: int = TILE,
                     seed: int = 42, frame: int = 0, variants: int = 8) -> Image.Image:
    """Assemble a patch from an explicit corner grid (shape (rows+1, cols+1),
    1 = upper terrain at that corner). Each cell gets a position-hashed variant
    so texture/edge detail differs tile-to-tile (no visible repetition) while
    seams stay exact. Tiles come from the 16-set, so the result is seamless."""
    rows, cols = grid.shape[0] - 1, grid.shape[1] - 1
    cache: dict[tuple[int, int], Image.Image] = {}
    out = Image.new("RGBA", (cols * tile, rows * tile))
    for r in range(rows):
        for c in range(cols):
            idx = corner_index(grid[r, c], grid[r, c + 1], grid[r + 1, c + 1], grid[r + 1, c])
            v = _variant(r, c, seed, max(1, variants))
            im = cache.get((idx, v))
            if im is None:
                im = cache[(idx, v)] = transition(upper, lower, index_corners(idx),
                                                  tile, seed, frame, variant=v)
            out.alpha_composite(im, (c * tile, r * tile))
    return out


def render_map(upper: str, lower: str, cols: int = 8, rows: int = 8,
               tile: int = TILE, seed: int = 42, frame: int = 0,
               threshold: float = 0.5) -> Image.Image:
    """Assemble a cols x rows patch from a coherent noise corner grid — for
    eyeballing that transitions tile seamlessly in situ."""
    field = value_noise(cols + 1, rows + 1, seed=seed, octaves=2, base_freq=2)
    grid = (field >= threshold).astype(int)
    return render_from_grid(upper, lower, grid, tile, seed, frame)


def manifest(upper: str, lower: str) -> dict:
    """Describe the tileset for the game (bit order + per-index corner states)."""
    return {
        "type": "autotile",
        "scheme": "corner-4bit-wang",
        "upper": upper,
        "lower": lower,
        "bits": {"NW": NW, "NE": NE, "SE": SE, "SW": SW},
        "corner_order": ["nw", "ne", "se", "sw"],
        "tiles": {idx: dict(zip(("nw", "ne", "se", "sw"), index_corners(idx)))
                  for idx in range(16)},
        "note": "1 = upper terrain at that corner. index = NW|NE<<1|SE<<2|SW<<3.",
    }
