"""Roads and paths.

A road is just a *linear* autotile feature: grass is the upper terrain, the road
surface (path / cobble / gravel / sand) is the lower terrain, and the corner
autotile gives the grassy fringe along both sides for free. We build a corner
grid (1 = grass, 0 = road) describing where the road runs, then render it with
the seamless 16-tile set.

Layouts: 'horizontal', 'vertical', 'cross', 'curve', 'plaza'. `width` is the
road thickness in tiles.
"""
from __future__ import annotations

import numpy as np

from .. import TILE
from . import autotile

LAYOUTS = ("horizontal", "vertical", "cross", "curve", "plaza")


def road_grid(cols: int, rows: int, layout: str = "cross", width: int = 2) -> np.ndarray:
    """Corner grid (rows+1, cols+1): 1 = grass, 0 = road."""
    g = np.ones((rows + 1, cols + 1), dtype=int)
    w = max(1, width)              # road width in tiles
    span = w + 1                   # corner lines to clear
    cr = (rows + 1) // 2 - span // 2
    cc = (cols + 1) // 2 - span // 2

    def band_h(lo):
        g[max(0, lo):lo + span, :] = 0

    def band_v(lo):
        g[:, max(0, lo):lo + span] = 0

    if layout in ("horizontal", "cross"):
        band_h(cr)
    if layout in ("vertical", "cross"):
        band_v(cc)
    if layout == "curve":
        g[max(0, cr):cr + span, :cc + span] = 0   # in from the left
        g[cr:, max(0, cc):cc + span] = 0          # turn down
    if layout == "plaza":
        g[max(0, cr - w):cr + span + w, max(0, cc - w):cc + span + w] = 0
    return g


def render(surface: str = "path", cols: int = 8, rows: int = 8, tile: int = TILE,
           seed: int = 42, layout: str = "cross", width: int = 2) -> "object":
    """Render a road of `surface` through grass with the given layout."""
    if layout not in LAYOUTS:
        raise ValueError(f"layout {layout!r} not in {LAYOUTS}")
    grid = road_grid(cols, rows, layout, width)
    return autotile.render_from_grid("grass", surface, grid, tile, seed)


def carve(grid: np.ndarray, surface: str, tile: int = TILE, seed: int = 42):
    """Render an arbitrary caller-supplied corner grid (1=grass, 0=road)."""
    return autotile.render_from_grid("grass", surface, grid, tile, seed)
