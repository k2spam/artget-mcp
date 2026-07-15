"""Procedural nature props (trees, bushes, rocks, flowers, etc.).

Each prop is centred in its tile, gets a 1px dark outline and a soft drop
shadow, and is snapped to the palette. Variety is seed-driven. Light from
top-left.

Pipeline per prop: draw raw silhouette -> quantize (snap colours, binary
alpha) -> outline -> drop_shadow. The shadow is added last and left
semi-transparent (it is excluded from the palette by design).
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .. import TILE
from ..canvas import drop_shadow, img, outline, radial_blob, shade_mask
from ..palette import hex_to_rgb, quantize

OUTLINE = "#231b04"

# green families for foliage
LEAF = {
    "dark":  ("#2f5a2b", "#345527", "#417a37"),   # (base, dark, light)
    "light": ("#4a7a3a", "#3e6631", "#5f8f46"),
    "pine":  ("#345527", "#2f5a2b", "#446a32"),
    "bush":  ("#4a8f4a", "#3e6631", "#5fa85f"),
}
WOOD = ("#6e4a2f", "#5a3a24", "#8f5a3a")
STONE = ("#7a7485", "#565061", "#948da3")


def _finalize(raw: Image.Image, shadow: bool = True) -> Image.Image:
    """Snap to palette, add outline, then a soft drop shadow."""
    q = quantize(raw)
    q = outline(q, OUTLINE)
    return drop_shadow(q, 1, 2, alpha=70) if shadow else q


def _blob(tile, cx, cy, r, seed, family, rough=0.32):
    base, dark, light = LEAF[family]
    mask = radial_blob(tile, cx, cy, r, seed=seed, rough=rough)
    return mask, shade_mask(mask, base, dark, light, seed=seed, mottle=0.3)


def tree_round(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    fam = "light" if seed % 2 else "dark"
    cx, r = tile / 2, tile * 0.30
    cy = tile * 0.38
    _, canopy = _blob(tile, cx, cy, r, seed, fam)
    # trunk
    d = ImageDraw.Draw(raw)
    tw = max(2, tile // 10)
    trunk_top = int(cy + r * 0.6)
    d.rectangle([cx - tw / 2, trunk_top, cx + tw / 2, tile - 2],
                fill=hex_to_rgb(WOOD[0]) + (255,))
    raw.alpha_composite(canopy)
    return _finalize(raw)


def tree_pine(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base, dark, light = (hex_to_rgb(c) for c in LEAF["pine"])
    tw = max(2, tile // 12)
    d.rectangle([tile / 2 - tw / 2, tile * 0.72, tile / 2 + tw / 2, tile - 2],
                fill=hex_to_rgb(WOOD[1]) + (255,))
    tiers = 3
    top, bottom = tile * 0.10, tile * 0.76
    for i in range(tiers):
        t0 = top + (bottom - top) * i / tiers
        t1 = top + (bottom - top) * (i + 1.2) / tiers
        half = tile * (0.14 + 0.10 * i)
        d.polygon([(tile / 2, t0), (tile / 2 - half, t1), (tile / 2 + half, t1)],
                  fill=base + (255,))
        # top-left highlight sliver
        d.polygon([(tile / 2, t0), (tile / 2 - half, t1), (tile / 2 - half * 0.3, t1)],
                  fill=light + (255,))
    return _finalize(raw)


def tree_palm(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base, dark, light = (hex_to_rgb(c) for c in LEAF["bush"])
    # curved trunk
    cx = tile * 0.5
    for i, y in enumerate(range(int(tile * 0.9), int(tile * 0.28), -1)):
        x = cx + np.sin(i / 6.0) * tile * 0.06
        d.point((x, y), fill=hex_to_rgb(WOOD[0]) + (255,))
        d.point((x + 1, y), fill=hex_to_rgb(WOOD[2]) + (255,))
    top = (cx + np.sin((tile * 0.62) / 6.0) * 0, tile * 0.28)
    # fronds
    for ang in (-1.0, -0.5, 0.0, 0.5, 1.0):
        ex = top[0] + np.cos(-1.3 + ang) * tile * 0.34
        ey = top[1] + np.sin(-1.3 + ang) * tile * 0.34 + tile * 0.12
        d.line([top, (ex, ey)], fill=base + (255,), width=2)
        d.line([top, (ex, ey)], fill=light + (255,), width=1)
    return _finalize(raw)


def bush(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    for dx, r, s in [(-tile * 0.14, tile * 0.20, seed), (tile * 0.15, tile * 0.18, seed + 1),
                     (0, tile * 0.24, seed + 2)]:
        _, blob = _blob(tile, tile / 2 + dx, tile * 0.62, r, s, "bush")
        raw.alpha_composite(blob)
    return _finalize(raw)


def stump(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base, dark, light = (hex_to_rgb(c) for c in WOOD)
    x0, x1 = tile * 0.32, tile * 0.68
    top, bot = tile * 0.42, tile * 0.80
    d.rectangle([x0, top, x1, bot], fill=base + (255,))
    d.ellipse([x0, top - tile * 0.08, x1, top + tile * 0.08], fill=light + (255,))
    d.ellipse([x0 + tile * 0.08, top - tile * 0.03, x1 - tile * 0.08, top + tile * 0.05],
              fill=dark + (255,))
    return _finalize(raw)


def boulder(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    mask = radial_blob(tile, tile / 2, tile * 0.58, tile * 0.30, seed=seed, rough=0.22)
    rock = shade_mask(mask, STONE[0], STONE[1], STONE[2], seed=seed, mottle=0.35)
    raw.alpha_composite(rock)
    # a couple of dark cracks
    d = ImageDraw.Draw(raw)
    rng = np.random.default_rng(seed + 3)
    for _ in range(2):
        x = int(rng.integers(tile * 0.35, tile * 0.65))
        d.line([(x, tile * 0.45), (x + int(rng.integers(-3, 3)), tile * 0.75)],
               fill=hex_to_rgb(STONE[1]) + (255,), width=1)
    return _finalize(raw)


def rock_small(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    rng = np.random.default_rng(seed)
    for _ in range(3):
        cx = float(rng.integers(int(tile * 0.3), int(tile * 0.7)))
        cy = float(rng.integers(int(tile * 0.55), int(tile * 0.75)))
        r = float(rng.integers(3, max(4, tile // 6)))
        mask = radial_blob(tile, cx, cy, r, seed=seed + int(cx), rough=0.2)
        raw.alpha_composite(shade_mask(mask, STONE[0], STONE[1], STONE[2], seed=seed))
    return _finalize(raw)


def flowers(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    green = hex_to_rgb("#4f7a3a")
    petals = [hex_to_rgb(c) for c in ("#e3d05a", "#d97b7b", "#e8e4dc", "#ffd982")]
    rng = np.random.default_rng(seed)
    for _ in range(6):
        x = int(rng.integers(4, tile - 4))
        y = int(rng.integers(tile // 2, tile - 3))
        d.line([(x, y), (x, y - 4)], fill=green + (255,), width=1)
        c = petals[int(rng.integers(len(petals)))]
        d.point((x, y - 5), fill=c + (255,))
        d.point((x - 1, y - 4), fill=c + (255,))
        d.point((x + 1, y - 4), fill=c + (255,))
    return _finalize(raw, shadow=False)


def mushroom(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    stem = hex_to_rgb("#e8c8a8")
    cap = hex_to_rgb("#b0453a")
    spot = hex_to_rgb("#e8e4dc")
    cx = tile / 2
    d.rectangle([cx - 2, tile * 0.55, cx + 2, tile * 0.78], fill=stem + (255,))
    d.pieslice([cx - tile * 0.22, tile * 0.35, cx + tile * 0.22, tile * 0.70],
               180, 360, fill=cap + (255,))
    for dx in (-4, 2, 5):
        d.point((cx + dx, tile * 0.50), fill=spot + (255,))
    return _finalize(raw)


def grass_tuft(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base, light = hex_to_rgb("#4f7a3a"), hex_to_rgb("#5f8f46")
    rng = np.random.default_rng(seed)
    cx = tile / 2
    for _ in range(6):
        x = cx + int(rng.integers(-tile // 4, tile // 4))
        h = int(rng.integers(tile // 4, tile // 2))
        lean = int(rng.integers(-2, 3))
        c = base if rng.random() < 0.6 else light
        d.line([(x, tile - 3), (x + lean, tile - 3 - h)], fill=c + (255,), width=1)
    return _finalize(raw, shadow=False)


def reeds(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base = hex_to_rgb("#446a32")
    head = hex_to_rgb("#7a5238")
    rng = np.random.default_rng(seed)
    for _ in range(4):
        x = int(rng.integers(6, tile - 6))
        h = int(rng.integers(tile // 2, int(tile * 0.75)))
        d.line([(x, tile - 2), (x, tile - 2 - h)], fill=base + (255,), width=1)
        d.rectangle([x - 1, tile - 2 - h - 3, x + 1, tile - 2 - h], fill=head + (255,))
    return _finalize(raw, shadow=False)


_SKULL = [
    "................",
    "................",
    "....OOOOOO......",
    "...OWWWWWWO.....",
    "..OWWWWWWWWO....",
    "..OWWWWWWWWO....",
    "..OWOOWWOOWO....",
    "..OWOOWWOOWO....",
    "..OWWWWWWWWO....",
    "...OWWOOWWO.....",
    "....OWWWWO......",
    "....OWOWOWO.....",
    "....OWOWOWO.....",
    ".....OOOOO......",
    "................",
    "................",
]


def skull(tile: int = TILE, seed: int = 42) -> Image.Image:
    from ..canvas import from_map
    raw16 = from_map(_SKULL, {"O": OUTLINE, "W": "#e8e8e0"})
    raw = raw16.resize((tile, tile), Image.NEAREST) if tile != 16 else raw16
    return drop_shadow(quantize(raw), 1, 2, alpha=70)


def fallen_branch(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    wood, wdark = hex_to_rgb("#6e4a2f"), hex_to_rgb("#5a3a24")
    rng = np.random.default_rng(seed)
    y = tile // 2 + int(rng.integers(-3, 4))
    x0 = int(tile * 0.15)
    pts = [(x0, y)]
    x = x0
    while x < tile * 0.85:
        x += int(rng.integers(3, 6))
        y += int(rng.integers(-2, 3))
        pts.append((x, y))
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=wood + (255,), width=2)
        d.line([pts[i], pts[i + 1]], fill=wdark + (255,), width=1)
    # a couple of small forks
    for _ in range(2):
        i = int(rng.integers(1, len(pts) - 1))
        bx, by = pts[i]
        d.line([(bx, by), (bx + int(rng.integers(-4, 5)), by - int(rng.integers(3, 6)))],
               fill=wood + (255,), width=1)
    return _finalize(raw)


def flat_rock(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    base, dark, light = (hex_to_rgb(c) for c in STONE)
    cx, cy = tile / 2, tile * 0.60
    rw, rh = tile * 0.30, tile * 0.16
    d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh + tile * 0.10], fill=dark + (255,))  # body
    d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=base + (255,))                # flat top
    d.ellipse([cx - rw * 0.7, cy - rh * 0.8, cx + rw * 0.2, cy], fill=light + (255,))  # highlight
    return _finalize(raw)


def mushroom_cluster(tile: int = TILE, seed: int = 42) -> Image.Image:
    raw = img(tile)
    d = ImageDraw.Draw(raw)
    rng = np.random.default_rng(seed)
    stem = hex_to_rgb("#e8c8a8")
    caps = ["#b0453a", "#cc6452", "#8f4f2f"]
    spot = hex_to_rgb("#e8e4dc")
    for k in range(3):
        cx = tile / 2 + (k - 1) * tile * 0.16 + int(rng.integers(-2, 3))
        sc = 0.16 - 0.03 * (k % 2)
        base = tile * 0.78 - (k % 2) * tile * 0.08
        d.rectangle([cx - 1, base - tile * 0.12, cx + 1, base], fill=stem + (255,))
        cap = hex_to_rgb(caps[int(rng.integers(len(caps)))])
        d.pieslice([cx - tile * sc, base - tile * 0.24, cx + tile * sc, base - tile * 0.06],
                   180, 360, fill=cap + (255,))
        d.point((cx, base - tile * 0.15), fill=spot + (255,))
    return _finalize(raw)


PROPS = {
    "tree_round": tree_round, "tree_pine": tree_pine, "tree_palm": tree_palm,
    "bush": bush, "stump": stump, "boulder": boulder, "rock_small": rock_small,
    "flat_rock": flat_rock, "flowers": flowers, "mushroom": mushroom,
    "mushroom_cluster": mushroom_cluster, "grass_tuft": grass_tuft,
    "reeds": reeds, "fallen_branch": fallen_branch, "skull": skull,
}

KINDS = tuple(PROPS)


def make(kind: str, tile: int = TILE, seed: int = 42) -> Image.Image:
    if kind not in PROPS:
        raise ValueError(f"unknown prop {kind!r}; choices: {sorted(PROPS)}")
    return PROPS[kind](tile, seed)


def generate(kinds=None, tile: int = TILE, seed: int = 42, count: int = 1) -> dict[str, list[Image.Image]]:
    kinds = kinds or KINDS
    return {k: [make(k, tile, seed + i) for i in range(max(1, count))] for k in kinds}
