"""Parametric village buildings and props — v2 (detailed, cozy).

Compact top-down houses packed with reference-level charm: varied shingle roofs
with a ridge cap, eave trim + shadow and moss flecks; framed 4-pane windows with
cream muntins, warm glow and shutters; timber framing (verticals + diagonal
braces) on plaster; stone base course; a framed door with a step and handle; a
capped chimney. Plus a decor kit (buckets, sacks, potted plants, flower boxes,
hanging/standing lanterns, an axe-in-stump, barrels, crates, log piles, fences,
well, market stall, haystack) for dressing the area around houses.

Everything is outlined, drop-shadowed, palette-snapped, lit from top-left.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..canvas import drop_shadow, outline
from ..palette import hex_to_rgb, quantize

OUTLINE = "#241d2b"


def _h(hexstr, a=255):
    r, g, b = hex_to_rgb(hexstr)
    return (r, g, b, a)


def _finalize(raw: Image.Image, sx=1, sy=2, salpha=70) -> Image.Image:
    q = quantize(raw)
    q = outline(q, OUTLINE)
    return drop_shadow(q, sx, sy, alpha=salpha)


# ---- houses ---------------------------------------------------------------

SIZES = {"S": (32, 32), "M": (46, 44), "L": (60, 56)}
ROOFS = {  # (base, dark, light) + warm/moss handled in _shingles
    "slate":  ("#6a6475", "#565061", "#7a7485"),
    "red":    ("#b0453a", "#8f4f2f", "#cc6452"),
    "thatch": ("#c4a86a", "#8f5a3a", "#e3d05a"),
}
WALLS = {
    "stone":  ("#a8a8a0", "#7a7485", "#c8c8c0"),
    "timber": ("#8f5a3a", "#6e4a2f", "#b0623a"),
    "frame":  ("#e8e4dc", "#6e4a2f", "#c9c2b5"),
}
DOORC, DOORFR, HANDLE, STEP = "#5a3a24", "#6e4a2f", "#ffd982", "#a8a8a0"
GLASS, GLASS2, MUNTIN, GLOW = "#4a5a8f", "#7fa8cc", "#e8e4dc", "#ffd982"
FOUND = "#7a7485"


def _shingles(d, x0, y0, x1, y1, cols, rng, moss=True):
    base, dark, light = (_h(c) for c in cols)
    warm, mossc = _h("#8f5a3a"), _h("#446a32")
    step = 3
    for row, yy in enumerate(range(y0, y1, step)):
        off = 2 if row % 2 else 0
        near_eave = yy > y1 - step * 2
        for xx in range(x0 - 2, x1 + 2, 4):
            r = rng.random()
            c = base
            if r < 0.16:
                c = light
            elif r < 0.32:
                c = dark
            elif r < 0.38:
                c = warm
            elif moss and near_eave and r < 0.44:
                c = mossc
            d.rectangle([xx + off, yy, xx + off + 3, min(yy + step - 1, y1)], fill=c)
            d.point((xx + off, yy), fill=dark)  # gap shadow between shingles


def _window(d, x, y, w, h, shutters=True):
    """Framed 4-pane window: wood frame, blue glass, cream muntins, glow, sill."""
    d.rectangle([x - 1, y - 1, x + w + 1, y + h + 1], fill=_h(DOORFR))     # frame
    d.rectangle([x, y, x + w, y + h], fill=_h(GLASS))                       # glass
    # glow in lower panes, lighter glass upper
    d.rectangle([x, y, x + w, y + h // 2], fill=_h(GLASS2))
    mx, my = x + w // 2, y + h // 2
    d.line([(mx, y), (mx, y + h)], fill=_h(MUNTIN))                         # muntins
    d.line([(x, my), (x + w, my)], fill=_h(MUNTIN))
    d.point((x + w - 2, y + h - 2), fill=_h(GLOW))
    d.line([(x - 1, y + h + 1), (x + w + 1, y + h + 1)], fill=_h(STEP))     # sill
    if shutters:
        d.rectangle([x - 3, y, x - 1, y + h], fill=_h("#8f5a3a"))
        d.rectangle([x + w + 1, y, x + w + 3, y + h], fill=_h("#8f5a3a"))


def _wall(d, x0, y0, x1, y1, material, cols, rng):
    base, dark, light = (_h(c) for c in cols)
    d.rectangle([x0, y0, x1, y1], fill=base)
    if material == "stone":
        for row, yy in enumerate(range(y0 + 2, y1, 4)):
            d.line([(x0, yy), (x1, yy)], fill=dark)
            off = 3 if row % 2 else 0
            for xx in range(x0 + off, x1, 6):
                d.line([(xx, yy), (xx, min(yy + 4, y1))], fill=dark)
                d.point((xx + 1, yy - 1), fill=light)
    elif material == "timber":
        for xx in range(x0 + 2, x1, 4):
            d.line([(xx, y0), (xx, y1)], fill=dark)
            d.line([(xx - 1, y0), (xx - 1, y1)], fill=light)
    else:  # frame: plaster + timber posts and diagonal braces
        d.rectangle([x0, y0, x0 + 2, y1], fill=dark)
        d.rectangle([x1 - 2, y0, x1, y1], fill=dark)
        d.line([(x0, y0), (x1, y0)], fill=dark)
        midx = (x0 + x1) // 2
        d.line([(midx, y0), (midx, y1)], fill=dark)
        d.line([(x0 + 2, y1), (midx, y0)], fill=dark)     # diagonal braces
        d.line([(x1 - 2, y1), (midx, y0)], fill=dark)


def house(size: str = "M", roof: str = "slate", walls: str = "timber",
          seed: int = 42) -> Image.Image:
    if size not in SIZES:
        raise ValueError(f"size {size!r} not in {sorted(SIZES)}")
    if roof not in ROOFS:
        raise ValueError(f"roof {roof!r} not in {sorted(ROOFS)}")
    if walls not in WALLS:
        raise ValueError(f"walls {walls!r} not in {sorted(WALLS)}")

    W, H = SIZES[size]
    pad = 4
    cw, ch = W + pad * 2, H + pad * 2
    raw = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    rng = np.random.default_rng(seed)

    x0, y0, x1, y1 = pad, pad, pad + W, pad + H
    roof_h = int(H * 0.5)
    roof_bottom = y0 + roof_h
    rb, rd, rl = (_h(c) for c in ROOFS[roof])

    # --- lower wall (facade) with foundation ---
    _wall(d, x0, roof_bottom, x1, y1, walls, WALLS[walls], rng)
    d.rectangle([x0, y1 - 2, x1, y1], fill=_h(FOUND))               # foundation course

    # door (framed, with step + handle)
    dw = max(5, int(W * 0.2))
    dx = (x0 + x1) // 2 - dw // 2
    dh = int((y1 - roof_bottom) * 0.72)
    dy = y1 - dh - 1
    d.rectangle([dx - 1, dy - 1, dx + dw + 1, y1 - 1], fill=_h(DOORFR))
    d.rectangle([dx, dy, dx + dw, y1 - 2], fill=_h(DOORC))
    d.line([(dx + dw // 2, dy), (dx + dw // 2, y1 - 2)], fill=_h("#3a2417"))
    d.point((dx + dw - 2, dy + dh // 2), fill=_h(HANDLE))           # handle
    d.rectangle([dx - 2, y1 - 1, dx + dw + 2, y1], fill=_h(STEP))   # step

    # windows flanking the door
    ww = max(6, int(W * 0.18))
    wh = max(6, int((y1 - roof_bottom) * 0.42))
    wy = roof_bottom + 3
    if size != "S":
        _window(d, x0 + 3, wy, ww, wh)
        _window(d, x1 - 3 - ww, wy, ww, wh)
        # flower box under the left window
        fx0, fx1 = x0 + 2, x0 + 4 + ww
        d.rectangle([fx0, wy + wh + 2, fx1, wy + wh + 5], fill=_h("#6e4a2f"))
        for fx in range(fx0 + 1, fx1, 2):
            d.point((fx, wy + wh + 1), fill=_h("#5aa843"))
            d.point((fx, wy + wh), fill=_h(["#d97b7b", "#e3d05a", "#e8e4dc"][fx % 3]))
    else:
        _window(d, (x0 + x1) // 2 - ww // 2, wy, ww, wh, shutters=False)

    # base bushes at a corner
    for bx in (x0 + 1, x1 - 4):
        if rng.random() < 0.8:
            d.ellipse([bx, y1 - 4, bx + 4, y1], fill=_h("#4a8f4a"))
            d.point((bx + 1, y1 - 3), fill=_h("#5fa85f"))

    # --- roof (overhanging, top-down) ---
    ox = 3
    d.rectangle([x0 - ox, y0, x1 + ox, roof_bottom], fill=rb)
    _shingles(d, x0 - ox, y0 + 1, x1 + ox, roof_bottom - 1, ROOFS[roof], rng)
    # ridge cap near top, eave trim + shadow
    ridge_y = y0 + max(2, roof_h // 4)
    d.line([(x0 - ox, ridge_y), (x1 + ox, ridge_y)], fill=rl)
    d.line([(x0 - ox, y0), (x1 + ox, y0)], fill=rl)                 # top trim
    d.line([(x0 - ox, roof_bottom - 1), (x1 + ox, roof_bottom - 1)], fill=rd)  # eave shadow
    d.line([(x0 - ox, roof_bottom), (x1 + ox, roof_bottom)], fill=_h("#3a2417"))

    # gable trim: a little peak vent centered
    vx = (x0 + x1) // 2
    d.rectangle([vx - 2, ridge_y + 2, vx + 2, ridge_y + 6], fill=_h(DOORFR))
    d.line([(vx, ridge_y + 2), (vx, ridge_y + 6)], fill=_h("#3a2417"))

    # chimney with cap (+ M/L)
    if size in ("M", "L"):
        chx = x1 - int(W * 0.28)
        d.rectangle([chx, y0 - 3, chx + 5, y0 + 6], fill=_h("#7a7485"))
        d.rectangle([chx - 1, y0 - 4, chx + 6, y0 - 2], fill=_h("#948da3"))  # cap
        for k in range(3):  # faint smoke
            d.point((chx + 2 + k, y0 - 6 - k * 2), fill=_h("#c8c8c0"))

    return _finalize(raw, sy=3, salpha=85)


# ---- structural props -----------------------------------------------------

def fence(gate: bool = False, tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, dark, light = _h("#8f5a3a"), _h("#5a3a24"), _h("#b0623a")
    top = tile // 2
    for px in (tile // 5, tile - tile // 5):
        d.rectangle([px - 1, top - 5, px + 1, tile - 4], fill=wood)
        d.point((px - 1, top - 5), fill=light)
    for ry in (top, top + 6):
        d.rectangle([0, ry, tile - 1, ry + 1], fill=wood)
        d.line([(0, ry + 2), (tile - 1, ry + 2)], fill=dark)
    if gate:
        gx0, gx1 = tile // 5 + 2, tile - tile // 5 - 2
        d.rectangle([gx0, top - 4, gx1, tile - 5], fill=wood)
        for gx in range(gx0, gx1, 3):
            d.line([(gx, top - 4), (gx, tile - 5)], fill=dark)
        d.point((gx1 - 2, (top + tile - 5) // 2), fill=_h(HANDLE))
    return _finalize(raw, sy=1, salpha=60)


def well(tile: int = 40, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    stone, sdark, slight = _h("#a8a8a0"), _h("#7a7485"), _h("#c8c8c0")
    wood, wdark = _h("#8f5a3a"), _h("#5a3a24")
    cx = tile // 2
    d.ellipse([cx - 10, tile - 20, cx + 10, tile - 4], fill=stone)
    d.ellipse([cx - 7, tile - 17, cx + 7, tile - 7], fill=_h("#3a3a44"))
    d.ellipse([cx - 5, tile - 15, cx + 5, tile - 10], fill=_h("#4a5a8f"))   # water
    for a in range(0, 360, 40):
        x = cx + int(9 * np.cos(np.radians(a)))
        y = (tile - 12) + int(7 * np.sin(np.radians(a)))
        d.point((x, y), fill=sdark)
    d.rectangle([cx - 9, tile - 30, cx - 7, tile - 12], fill=wood)
    d.rectangle([cx + 7, tile - 30, cx + 9, tile - 12], fill=wood)
    d.polygon([(cx - 13, tile - 30), (cx + 13, tile - 30), (cx, tile - 40)], fill=_h("#b0453a"))
    d.line([(cx - 13, tile - 30), (cx, tile - 40)], fill=_h("#cc6452"))
    d.rectangle([cx - 2, tile - 20, cx + 2, tile - 18], fill=wdark)          # bucket on rope
    return _finalize(raw, sy=2, salpha=75)


def market_stall(tile: int = 44, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark = _h("#8f5a3a"), _h("#5a3a24")
    red, cream = _h("#b0453a"), _h("#e8e4dc")
    x0, x1 = 4, tile - 4
    d.rectangle([x0, tile - 14, x1, tile - 4], fill=wood)
    d.line([(x0, tile - 14), (x1, tile - 14)], fill=wdark)
    d.rectangle([x0, tile - 30, x0 + 2, tile - 4], fill=wdark)
    d.rectangle([x1 - 2, tile - 30, x1, tile - 4], fill=wdark)
    for i, xx in enumerate(range(x0 - 2, x1 + 2, 5)):
        d.rectangle([xx, tile - 34, xx + 4, tile - 26], fill=red if i % 2 else cream)
    d.line([(x0 - 2, tile - 26), (x1 + 2, tile - 26)], fill=wdark)
    # goods on the counter
    d.ellipse([x0 + 4, tile - 18, x0 + 8, tile - 14], fill=_h("#b0453a"))
    d.ellipse([x0 + 10, tile - 17, x0 + 13, tile - 14], fill=_h("#e3d05a"))
    return _finalize(raw, sy=2, salpha=70)


# ---- decor props ----------------------------------------------------------

def barrel(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, wl = _h("#8f5a3a"), _h("#5a3a24"), _h("#b0623a")
    cx = tile // 2
    x0, x1, y0, y1 = cx - 7, cx + 7, tile - 22, tile - 4
    d.rectangle([x0, y0, x1, y1], fill=wood)
    d.line([(cx - 4, y0), (cx - 4, y1)], fill=wl)
    for hy in (y0 + 2, (y0 + y1) // 2, y1 - 2):
        d.line([(x0, hy), (x1, hy)], fill=wdark)
    d.ellipse([x0, y0 - 2, x1, y0 + 3], fill=wl)
    return _finalize(raw, sy=1, salpha=65)


def crate(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, wl = _h("#94684a"), _h("#5a3a24"), _h("#b0623a")
    cx = tile // 2
    x0, x1, y0, y1 = cx - 8, cx + 8, tile - 20, tile - 4
    d.rectangle([x0, y0, x1, y1], fill=wood)
    d.rectangle([x0, y0, x1, y0 + 2], fill=wl)
    d.line([(x0, y1), (x1, y0)], fill=wdark)
    d.line([(x0, y0), (x1, y1)], fill=wdark)
    d.rectangle([x0, y0, x1, y1], outline=wdark)
    return _finalize(raw, sy=1, salpha=65)


def bucket(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, water = _h("#94684a"), _h("#5a3a24"), _h("#4a5a8f")
    cx = tile // 2
    x0, x1, y0, y1 = cx - 5, cx + 5, tile - 14, tile - 4
    d.polygon([(x0, y0), (x1, y0), (x1 - 1, y1), (x0 + 1, y1)], fill=wood)   # tapered
    d.ellipse([x0, y0 - 2, x1, y0 + 2], fill=water)                          # water top
    d.arc([x0 - 1, y0 - 5, x1 + 1, y0 + 3], 180, 360, fill=wdark)            # handle
    d.line([(x0, (y0 + y1) // 2), (x1, (y0 + y1) // 2)], fill=wdark)
    return _finalize(raw, sy=1, salpha=60)


def sack(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    cloth, cdark, cl = _h("#cbb08a"), _h("#94684a"), _h("#e3cf94")
    cx = tile // 2
    d.ellipse([cx - 6, tile - 16, cx + 6, tile - 3], fill=cloth)
    d.ellipse([cx - 6, tile - 16, cx - 1, tile - 5], fill=cl)
    d.polygon([(cx - 3, tile - 16), (cx + 3, tile - 16), (cx + 2, tile - 19), (cx - 2, tile - 19)],
              fill=cdark)  # tied neck
    d.line([(cx, tile - 14), (cx, tile - 5)], fill=cdark)
    return _finalize(raw, sy=1, salpha=60)


def potted_plant(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    pot, potd = _h("#b0623a"), _h("#8f4f2f")
    cx = tile // 2
    d.polygon([(cx - 5, tile - 8), (cx + 5, tile - 8), (cx + 4, tile - 3), (cx - 4, tile - 3)], fill=pot)
    d.line([(cx - 5, tile - 8), (cx + 5, tile - 8)], fill=potd)
    d.ellipse([cx - 6, tile - 18, cx + 6, tile - 7], fill=_h("#4a8f4a"))
    d.ellipse([cx - 6, tile - 18, cx, tile - 10], fill=_h("#5fa85f"))
    rng = np.random.default_rng(seed)
    for _ in range(3):
        x = cx + int(rng.integers(-4, 5)); y = tile - 16 + int(rng.integers(0, 6))
        d.point((x, y), fill=_h(["#d97b7b", "#e3d05a", "#e8e4dc"][int(rng.integers(3))]))
    return _finalize(raw, sy=1, salpha=60)


def flower_box(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark = _h("#8f5a3a"), _h("#5a3a24")
    x0, x1, y = 6, tile - 6, tile - 10
    d.rectangle([x0, y, x1, y + 5], fill=wood)
    d.line([(x0, y), (x1, y)], fill=wdark)
    rng = np.random.default_rng(seed)
    for fx in range(x0 + 1, x1, 2):
        d.line([(fx, y), (fx, y - 3)], fill=_h("#4a8f4a"))
        d.point((fx, y - 4), fill=_h(["#d97b7b", "#e3d05a", "#e8e4dc", "#ffd982"][int(rng.integers(4))]))
    return _finalize(raw, sy=1, salpha=55)


def lantern(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    metal, mdark = _h("#565061"), _h("#241d2b")
    cx = tile // 2
    d.rectangle([cx - 1, tile - 26, cx + 1, tile - 4], fill=metal)
    d.line([(cx, tile - 26), (cx + 5, tile - 26)], fill=metal)
    lx, ly = cx + 5, tile - 24
    d.rectangle([lx - 3, ly, lx + 3, ly + 7], fill=mdark)
    d.rectangle([lx - 2, ly + 1, lx + 2, ly + 6], fill=_h(GLOW))
    d.point((lx, ly + 3), fill=_h("#e8e4dc"))
    return _finalize(raw, sy=1, salpha=55)


def axe_stump(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, wl = _h("#8f5a3a"), _h("#5a3a24"), _h("#c4a86a")
    cx = tile // 2
    x0, x1, y0, y1 = cx - 7, cx + 7, tile - 12, tile - 4
    d.rectangle([x0, y0, x1, y1], fill=wood)
    d.ellipse([x0, y0 - 3, x1, y0 + 3], fill=wl)               # top rings
    d.ellipse([x0 + 3, y0 - 1, x1 - 3, y0 + 2], fill=wdark)
    # axe: handle + head stuck in the stump
    d.line([(cx, y0), (cx + 7, y0 - 10)], fill=wdark, width=2)
    d.polygon([(cx - 2, y0 - 2), (cx + 2, y0 - 5), (cx + 2, y0 + 1)], fill=_h("#948da3"))
    return _finalize(raw, sy=1, salpha=65)


def woodpile(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, wl = _h("#94684a"), _h("#5a3a24"), _h("#c4a86a")
    r = 3
    for row, yy in enumerate((tile - 8, tile - 14)):
        n = 4 if row == 0 else 3
        for i in range(n):
            x = 6 + i * 7 + (3 if row else 0)
            d.ellipse([x, yy, x + 2 * r, yy + 2 * r], fill=wood)
            d.ellipse([x + 1, yy + 1, x + 2 * r - 1, yy + 2 * r - 1], fill=wl)
            d.point((x + r, yy + r), fill=wdark)
    return _finalize(raw, sy=1, salpha=65)


def signpost(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    wood, wdark, wl = _h("#8f5a3a"), _h("#5a3a24"), _h("#b0623a")
    cx = tile // 2
    d.rectangle([cx - 1, tile - 22, cx + 1, tile - 4], fill=wood)
    d.rectangle([cx - 8, tile - 24, cx + 9, tile - 17], fill=wl)
    d.rectangle([cx - 8, tile - 24, cx + 9, tile - 17], outline=wdark)
    d.line([(cx - 5, tile - 21), (cx + 3, tile - 21)], fill=wdark)
    d.line([(cx - 5, tile - 19), (cx + 5, tile - 19)], fill=wdark)
    return _finalize(raw, sy=1, salpha=60)


def haystack(tile: int = 32, seed: int = 42) -> Image.Image:
    raw = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
    d = ImageDraw.Draw(raw)
    hay, hdark, hl = _h("#e3d05a"), _h("#c4a86a"), _h("#ffd982")
    cx = tile // 2
    d.pieslice([cx - 11, tile - 22, cx + 11, tile - 2], 180, 360, fill=hay)
    d.rectangle([cx - 11, tile - 12, cx + 11, tile - 4], fill=hay)
    rng = np.random.default_rng(seed)
    for _ in range(10):
        x = int(rng.integers(cx - 9, cx + 9)); y = int(rng.integers(tile - 18, tile - 5))
        d.line([(x, y), (x + 2, y - 3)], fill=hdark)
    d.arc([cx - 11, tile - 22, cx + 11, tile - 2], 180, 360, fill=hl)
    return _finalize(raw, sy=1, salpha=65)


PROPS = {
    "fence": lambda tile=32, seed=42: fence(False, tile, seed),
    "gate": lambda tile=32, seed=42: fence(True, tile, seed),
    "well": well, "market_stall": market_stall,
    "barrel": barrel, "crate": crate, "bucket": bucket, "sack": sack,
    "potted_plant": potted_plant, "flower_box": flower_box, "lantern": lantern,
    "axe_stump": axe_stump, "woodpile": woodpile, "signpost": signpost,
    "haystack": haystack,
}

KINDS = tuple(PROPS)


def make_prop(kind: str, seed: int = 42) -> Image.Image:
    if kind not in PROPS:
        raise ValueError(f"unknown prop {kind!r}; choices: {sorted(PROPS)}")
    return PROPS[kind](seed=seed)


def catalog(seed: int = 42) -> dict[str, Image.Image]:
    out: dict[str, Image.Image] = {}
    combos = [("S", "thatch", "timber"), ("M", "slate", "frame"),
              ("M", "red", "stone"), ("L", "slate", "stone"), ("L", "thatch", "frame")]
    for sz, rf, wl in combos:
        out[f"house_{sz}_{rf}_{wl}"] = house(sz, rf, wl, seed)
    for k in PROPS:
        out[k] = make_prop(k, seed)
    return out
