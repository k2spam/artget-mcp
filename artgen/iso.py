"""Isometric prototype (experimental, separate from the top-down M1-M4 modules).

A 2:1 dimetric projection (like Fallout 1-2 / SimCity): world (x east, y south,
z up) -> screen. Buildings are drawn as boxes with two shaded wall faces plus a
tiled gable roof, which gives the volume the top-down tiles lack. Ground is
drawn as tessellating diamonds. Objects are composited back-to-front by depth.

This is a feel prototype: geometry + charm details on one house, on a small plot
with a flagstone path and a few props. Palette-snapped, outlined, top-left light.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .canvas import outline
from .palette import hex_to_rgb, quantize

# projection constants
HW, HH = 32, 16      # half-width / half-height of a ground diamond (64x32)
ZS = 20              # screen pixels per world unit of height
OUTLINE = "#241d2b"


def project(x: float, y: float, z: float = 0.0) -> tuple[float, float]:
    return ((x - y) * HW, (x + y) * HH - z * ZS)


def _rgb(hx, a=255):
    r, g, b = hex_to_rgb(hx)
    return (r, g, b, a)


def _shade(hx, f):
    """Multiply a hex colour by factor f (for face lighting)."""
    r, g, b = hex_to_rgb(hx)
    return (max(0, min(255, int(r * f))), max(0, min(255, int(g * f))),
            max(0, min(255, int(b * f))), 255)


class Sprite:
    """Accumulates world-space polygons/lines, renders to an RGBA image with a
    recorded anchor (screen pixel of world origin) so it can be placed on a map."""

    def __init__(self, margin=3):
        self.polys: list[tuple[list[tuple[float, float, float]], tuple]] = []
        self.lines: list[tuple[tuple, tuple, tuple, int]] = []
        self.margin = margin

    def poly(self, pts, color):
        self.polys.append((pts, color))
        return self

    def line(self, a, b, color, width=1):
        self.lines.append((a, b, color, width))
        return self

    def _screen(self, p):
        return project(*p)

    def render(self, do_outline=True, shadow=True):
        sp = [self._screen(p) for pts, _ in self.polys for p in pts]
        sp += [self._screen(p) for a, b, _, _ in self.lines for p in (a, b)]
        xs = [s[0] for s in sp]
        ys = [s[1] for s in sp]
        minx, miny, maxx, maxy = min(xs), min(ys), max(xs), max(ys)
        m = self.margin
        W = int(maxx - minx) + 2 * m + 2
        H = int(maxy - miny) + 2 * m + 2
        ax, ay = -minx + m, -miny + m           # world-origin pixel in sprite
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for pts, color in self.polys:
            d.polygon([(self._screen(p)[0] + ax, self._screen(p)[1] + ay) for p in pts],
                      fill=color)
        for a, b, color, w in self.lines:
            s0 = self._screen(a); s1 = self._screen(b)
            d.line([(s0[0] + ax, s0[1] + ay), (s1[0] + ax, s1[1] + ay)], fill=color, width=w)
        im = quantize(im)
        if do_outline:
            im = outline(im, OUTLINE)
            ax += 0; ay += 0
        if shadow:
            # soft ground shadow: cheap offset silhouette
            from .canvas import drop_shadow
            im = drop_shadow(im, 2, 1, alpha=60)
        return im, ax, ay


# ---- ground ---------------------------------------------------------------

# diamond vertices (in the 65x33 sprite) and named edges
_V = {"top": (HW, 0), "right": (2 * HW, HH), "bottom": (HW, 2 * HH), "left": (0, HH)}
_EDGES = {"NE": ("top", "right"), "SE": ("right", "bottom"),
          "SW": ("bottom", "left"), "NW": ("left", "top")}

# ground biomes -> (base, shade palette, detail palette)
BIOMES = {
    "grass":        ("#4f7a3a", ["#446a32", "#5f8f46", "#3e6631"], ["#3e6631", "#5f8f46"]),
    "meadow":       ("#5f8f46", ["#4f7a3a", "#7cc45e", "#446a32"], ["#5f8f46", "#7cc45e"]),
    "forest_floor": ("#3e6631", ["#345527", "#446a32", "#4a7a3a"], ["#345527", "#6e4a2f"]),
    "sand":         ("#d9c07f", ["#c4a86a", "#e3cf94", "#cbb08a"], ["#94684a", "#e3cf94"]),
    "dirt":         ("#6e4a2f", ["#5a3a24", "#7a5238", "#94684a"], ["#5a3a24", "#94684a"]),
    "stone":        ("#6a6475", ["#565061", "#7a7485", "#948da3"], ["#565061", "#948da3"]),
    "snow":         ("#e8e8e0", ["#c8c8c0", "#e8e4dc"], ["#948da3", "#e8e8e0"]),
    "path":         ("#cbb08a", ["#c4a86a", "#94684a"], ["#7a7485", "#94684a"]),
}


def _diamond_pts():
    return [_V["top"], _V["right"], _V["bottom"], _V["left"]]


def _scatter_diamond(d, rng, shades, det, n_shade=24, n_det=6):
    for _ in range(n_shade):
        u, v = rng.random(), rng.random()
        px, py = HW + (u - v) * HW, (u + v) * HH
        if 0 <= px < 2 * HW and 0 <= py < 2 * HH:
            d.point((px, py), fill=_rgb(shades[int(rng.integers(len(shades)))]))
    for _ in range(n_det):
        u, v = rng.random(), rng.random()
        d.point((HW + (u - v) * HW, (u + v) * HH), fill=_rgb(det[int(rng.integers(len(det)))]))


def _fringe(d, rng, edges, colors, steps=7, reach=4):
    """Draw little tufts overhanging inward along the given diamond edges."""
    cx, cy = HW, HH
    for e in edges:
        (n0, n1) = _EDGES[e]
        (ax, ay), (bx, by) = _V[n0], _V[n1]
        for t in np.linspace(0.1, 0.9, steps):
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            inx, iny = cx - x, cy - y
            ln = (inx * inx + iny * iny) ** 0.5 or 1
            j = rng.random() * reach
            gx, gy = x + inx / ln * j, y + iny / ln * j
            c = _rgb(colors[int(rng.integers(len(colors)))])
            d.point((gx, gy), fill=c)
            d.point((gx - 1, gy - 1), fill=c)
            d.point((gx + 1, gy - 1), fill=c)


def _uv_grid():
    """Per-pixel (u,v) barycentric coords of the diamond sprite; inside mask."""
    W, H = 2 * HW + 1, 2 * HH + 1
    dx = (np.arange(W) - HW)[None, :].astype(float)
    dy = np.arange(H)[:, None].astype(float)
    u = (dx / HW + dy / HH) / 2
    v = (dy / HH - dx / HW) / 2
    inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
    return u, v, inside


_UV_U, _UV_V, _UV_IN = _uv_grid()

_FIELD_N = 192
_FIELD_STEP = 8           # field cells per world tile (patch size ~ several tiles)
_field_cache: dict[int, np.ndarray] = {}


def _global_field(seed: int) -> np.ndarray:
    """A large tileable noise field sampled by WORLD position so ground mottling
    flows continuously across diamonds (no per-tile rhythm)."""
    if seed not in _field_cache:
        from .canvas import value_noise
        _field_cache[seed] = value_noise(_FIELD_N, _FIELD_N, seed=seed,
                                          octaves=4, base_freq=6, tileable=True)
    return _field_cache[seed]


def diamond(kind="grass", seed=0, world=(0, 0), fringe=(), fringe_kind="grass",
            field_seed=7):
    """A ground diamond (64x32) for a biome. Mottling is sampled from a global
    world-space noise field so soft patches flow across neighbouring tiles.
    Optional vegetation fringe on selected edges softens biome/path borders."""
    base, shades, det = BIOMES.get(kind, BIOMES["grass"])
    pal = np.array([hex_to_rgb(base), hex_to_rgb(shades[0]),
                    hex_to_rgb(shades[min(1, len(shades) - 1)])], dtype=np.uint8)
    gf = _global_field(field_seed)
    wi, wj = world
    ui = (((wi + _UV_U) * _FIELD_STEP).astype(int)) % _FIELD_N
    vi = (((wj + _UV_V) * _FIELD_STEP).astype(int)) % _FIELD_N
    val = gf[vi, ui]
    idx = np.zeros(val.shape, int)
    idx[val < 0.42] = 1
    idx[val > 0.70] = 2
    W, H = 2 * HW + 1, 2 * HH + 1
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[..., :3] = pal[idx]
    arr[..., 3] = np.where(_UV_IN, 255, 0)
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed + 3)
    for _ in range(5):
        uu, vv = rng.random(), rng.random()
        d.point((HW + (uu - vv) * HW, (uu + vv) * HH), fill=_rgb(det[int(rng.integers(len(det)))]))
    if fringe:
        fcol = BIOMES.get(fringe_kind, BIOMES["grass"])[1]
        _fringe(d, rng, fringe, fcol, steps=10, reach=6)
    return quantize(im)


# ---- water / lakes --------------------------------------------------------

def water_tile(frame=0, seed=0, foam=()):
    """Animated lake diamond: base blue + moving ripples; foam tufts on edges
    bordering land (pass the set of land-facing edges)."""
    im = Image.new("RGBA", (2 * HW + 1, 2 * HH + 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(_diamond_pts(), fill=_rgb("#3f75ad"))
    rng = np.random.default_rng(seed)
    # ripple dashes drifting with frame
    for k in range(7):
        u = (rng.random() + frame * 0.12) % 1.0
        v = rng.random()
        px, py = HW + (u - v) * HW, (u + v) * HH
        if 2 <= px < 2 * HW - 2 and 0 <= py < 2 * HH:
            c = _rgb("#7fa8cc" if (k + frame) % 2 else "#2f5e8f")
            d.point((px, py), fill=c); d.point((px + 1, py), fill=c)
    # foam along land edges, animated width
    cx, cy = HW, HH
    for e in foam:
        (n0, n1) = _EDGES[e]
        (ax, ay), (bx, by) = _V[n0], _V[n1]
        for t in np.linspace(0.08, 0.92, 9):
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            inx, iny = cx - x, cy - y
            ln = (inx * inx + iny * iny) ** 0.5 or 1
            j = 2 + ((int(t * 9) + frame) % 2) * 1.5
            fx, fy = x + inx / ln * j, y + iny / ln * j
            col = _rgb("#e8e8e0" if (int(t * 9) + frame) % 2 else "#7fa8cc")
            d.point((fx, fy), fill=col)
            d.point((fx - 1, fy), fill=col)
    return quantize(im)


def coast_tile(corners, seed=0, frame=0, land_kind="grass", world=(0, 0)):
    """Shoreline diamond: `corners`=(top,right,bottom,left) booleans (1=water).
    The water/land boundary is a bilinear corner field + edge-vanishing noise,
    so it's an organic curve INSIDE the diamond and stays seamless with
    neighbours (shared corners) — this makes lake edges non-rectangular. Foam
    runs along the waterline."""
    if not any(corners):
        return diamond(land_kind, seed, world=world)
    if all(corners):
        return water_tile(frame, seed)
    from .canvas import value_noise
    land = np.asarray(diamond(land_kind, seed, world=world).convert("RGB"))
    water = np.asarray(water_tile(frame, seed).convert("RGB"))
    u, v = np.clip(_UV_U, 0, 1), np.clip(_UV_V, 0, 1)
    c00, c10, c11, c01 = (float(x) for x in corners)   # top,right,bottom,left
    field = (c00 * (1 - u) * (1 - v) + c10 * u * (1 - v)
             + c11 * u * v + c01 * (1 - u) * v)
    win = np.sin(np.pi * u) * np.sin(np.pi * v)
    n = value_noise(20, 20, seed=seed + 5, octaves=3, base_freq=4, tileable=True)
    ui = np.clip((u * 19), 0, 19).astype(int)
    vi = np.clip((v * 19), 0, 19).astype(int)
    field = field + (n[vi, ui] - 0.5) * 2 * 0.33 * win
    water_mask = (field > 0.5) & _UV_IN
    out = np.where(water_mask[..., None], water, land)
    land_in = _UV_IN & ~water_mask
    adj = np.zeros_like(water_mask)
    adj[:-1, :] |= land_in[1:, :]; adj[1:, :] |= land_in[:-1, :]
    adj[:, :-1] |= land_in[:, 1:]; adj[:, 1:] |= land_in[:, :-1]
    foam = water_mask & adj
    out[foam] = np.array(hex_to_rgb("#e8e8e0" if frame % 2 else "#7fa8cc"), np.uint8)
    arr = np.zeros((out.shape[0], out.shape[1], 4), dtype=np.uint8)
    arr[..., :3] = out
    arr[..., 3] = np.where(_UV_IN, 255, 0)
    return quantize(Image.fromarray(arr, "RGBA"))


def reeds_patch(seed=1):
    """Cattails / reeds clump (billboard), anchored at base centre."""
    def draw(dd):
        rng = np.random.default_rng(seed)
        for _ in range(7):
            x = 8 + int(rng.integers(0, 20))
            h = 12 + int(rng.integers(0, 10))
            dd.line([(x, 30), (x, 30 - h)], fill=_rgb("#446a32"), width=1)
            if rng.random() < 0.6:  # cattail head
                dd.rectangle([x - 1, 30 - h - 3, x + 1, 30 - h], fill=_rgb("#6e4a2f"))
    return _billboard(draw, 36, 34, 18, 30, shadow_r=0)


def lily_pads(seed=1):
    def draw(dd):
        rng = np.random.default_rng(seed)
        for _ in range(4):
            x, y = int(rng.integers(4, 28)), int(rng.integers(10, 24))
            r = int(rng.integers(3, 5))
            dd.ellipse([x - r, y - r // 2, x + r, y + r // 2], fill=_rgb("#4a8f4a"))
            dd.point((x, y), fill=_rgb("#345527"))
            if rng.random() < 0.5:
                dd.point((x + 1, y - 1), fill=_rgb("#d97b7b"))  # flower
    return _billboard(draw, 32, 28, 16, 20, shadow_r=0)


def algae(seed=1):
    def draw(dd):
        rng = np.random.default_rng(seed)
        for _ in range(10):
            x, y = int(rng.integers(2, 30)), int(rng.integers(8, 24))
            dd.point((x, y), fill=_rgb("#446a32"))
            dd.point((x + 1, y), fill=_rgb("#345527"))
    return _billboard(draw, 32, 28, 16, 18, shadow_r=0)


def boat(frame=0, seed=1):
    """Small rowboat that bobs (frame shifts it a pixel)."""
    def draw(dd):
        dy = frame % 2
        wood, dark, light = _rgb("#8f5a3a"), _rgb("#5a3a24"), _rgb("#b0623a")
        # hull (iso ellipse)
        dd.ellipse([4, 14 + dy, 44, 30 + dy], fill=wood)
        dd.ellipse([8, 15 + dy, 40, 26 + dy], fill=dark)
        dd.ellipse([9, 15 + dy, 39, 24 + dy], fill=light)
        dd.line([(24, 15 + dy), (24, 26 + dy)], fill=dark)   # bench
        dd.rectangle([23, 4 + dy, 25, 16 + dy], fill=wood)   # mast
    return _billboard(draw, 50, 36, 24, 30, shadow_r=14)


# ---- house ----------------------------------------------------------------

WALL_MATERIALS = {                       # (base, dark, light)
    "log":     ("#94684a", "#6e4a2f", "#b0623a"),
    "timber":  ("#8f5a3a", "#5a3a24", "#b0623a"),
    "plaster": ("#e8e4dc", "#6e4a2f", "#c9c2b5"),
    "stone":   ("#a8a8a0", "#7a7485", "#c8c8c0"),
}
ROOF_TYPES = {
    "red":    ("#b0453a", "#8f4f2f", "#cc6452"),
    "slate":  ("#6a6475", "#565061", "#7a7485"),
    "thatch": ("#c4a86a", "#8f5a3a", "#e3d05a"),
    "wood":   ("#8f5a3a", "#5a3a24", "#b0623a"),
}


def plan_windows(umax, zmax, n, exclude=None, zc=None):
    """Positions of `n` windows on a wall of extent `umax` x `zmax`, GUARANTEED
    to stay within the wall (with frame margin). Used by the house and by the
    validation test. `exclude` = (u0,u1) door span to avoid; `zc` overrides the
    vertical centre. Returns list of (uc, zc, w, h)."""
    w, h, fr = 0.5, 0.55, 0.14
    half = w / 2 + fr
    if umax < 2 * half + 0.15 or zmax < h + 2 * fr + 0.15:
        return []
    zc = zmax * 0.55 if zc is None else zc
    zc = min(max(zc, h / 2 + fr + 0.1), zmax - h / 2 - fr - 0.05)
    lo, hi = half + 0.1, umax - half - 0.1
    if n <= 1:
        cs = [(lo + hi) / 2]
    else:
        cs = [lo + (hi - lo) * k / (n - 1) for k in range(n)]
    out = []
    for uc in cs:
        if exclude and exclude[0] - half < uc < exclude[1] + half:
            continue
        out.append((uc, zc, w, h))
    return out


def house(walls="timber", roof="red", fx=2.0, fy=2.4, wh=1.5, rh=1.1,
          seed=42, smoke=True, chimney=True, storeys=1):
    """Isometric house: two shaded walls of `walls` material, gable roof of
    `roof` type, framed windows (validated to stay within the walls), a door
    with awning, optional chimney + smoke, and charm details.

    walls in log/timber/plaster/stone; roof in red/slate/thatch/wood.
    storeys 1 or 2 (2 raises the walls, adds a beltcourse + an upper window row).
    Returns (sprite, anchor_x, anchor_y); world origin (0,0,0) = NW ground corner."""
    if storeys == 2:
        wh = max(wh, 2.6)
    wb, wd, wl = (WALL_MATERIALS.get(walls, WALL_MATERIALS["timber"]))
    rb0, rd0, rl0 = (ROOF_TYPES.get(roof, ROOF_TYPES["red"]))
    s = Sprite(margin=4)
    rng = np.random.default_rng(seed)
    roof_lit, roof_dark = _shade(rl0, 1.0), _shade(rd0, 1.0)

    def swall(u0, u1, z0, z1, color):    # rect on left face (y=fy, lit)
        s.poly([(u0, fy, z0), (u1, fy, z0), (u1, fy, z1), (u0, fy, z1)], color)

    def ewall(v0, v1, z0, z1, color):    # rect on right face (x=fx, shaded)
        s.poly([(fx, v0, z0), (fx, v1, z0), (fx, v1, z1), (fx, v0, z1)], color)

    def material(put, umax, factor):
        base, dark, light = _shade(wb, factor), _shade(wd, factor), _shade(wl, factor)
        put(0, umax, 0, wh, base)
        if walls == "log":
            z = 0.0
            while z < wh:
                put(0, umax, z, z + 0.05, dark)
                put(0, umax, z + 0.26, z + 0.3, light)
                z += 0.32
            put(0, 0.16, 0, wh, light); put(umax - 0.16, umax, 0, wh, _shade(wb, factor * 0.85))
        elif walls == "timber":
            u = 0.15
            while u < umax:
                put(u, u + 0.05, 0, wh, dark)
                u += 0.34
        elif walls == "plaster":
            put(0, 0.12, 0, wh, dark); put(umax - 0.12, umax, 0, wh, dark)
            put(0, umax, wh - 0.12, wh, dark); put(0, umax, wh * 0.5, wh * 0.5 + 0.1, dark)
            put(umax * 0.5 - 0.05, umax * 0.5 + 0.05, 0, wh, dark)
        else:  # stone
            z, row = 0.0, 0
            while z < wh:
                put(0, umax, z, z + 0.04, dark)
                off = 0.25 if row % 2 else 0.0
                u = off
                while u < umax:
                    put(u, u + 0.03, z, z + 0.26, dark)
                    u += 0.5
                z += 0.28; row += 1

    # walls
    material(swall, fx, 1.0)
    material(ewall, fy, 0.82)
    # stone foundation course (skip for stone walls)
    if walls != "stone":
        swall(0, fx, 0, 0.16, _rgb("#7a7485"))
        ewall(0, fy, 0, 0.16, _rgb("#565061"))

    frame, glass, glow, muntin = _rgb("#6e4a2f"), _rgb("#4a5a8f"), _rgb("#ffd982"), _rgb("#e8e4dc")

    def draw_window(put, uc, zc, w, h, lit=True):
        g = glass if lit else _shade("#4a5a8f", 0.85)
        put(uc - w / 2 - 0.06, uc + w / 2 + 0.06, zc - h / 2 - 0.06, zc + h / 2 + 0.06, frame)
        put(uc - w / 2, uc + w / 2, zc - h / 2, zc + h / 2, g)
        put(uc - 0.03, uc + 0.03, zc - h / 2, zc + h / 2, muntin)
        put(uc - w / 2, uc + w / 2, zc - 0.03, zc + 0.03, muntin)
        if lit:
            put(uc + w / 2 - 0.12, uc + w / 2 - 0.02, zc - h / 2 + 0.02, zc, glow)
        put(uc - w / 2 - 0.08, uc + w / 2 + 0.08, zc - h / 2 - 0.09, zc - h / 2 - 0.04, _rgb("#cbb08a"))
        put(uc - w / 2 - 0.14, uc - w / 2 - 0.05, zc - h / 2, zc + h / 2, _rgb("#8f5a3a"))
        put(uc + w / 2 + 0.05, uc + w / 2 + 0.14, zc - h / 2, zc + h / 2, _rgb("#8f5a3a"))

    # door on the front (left/SW) face + frame + handle + step
    dw = 0.5
    dcx = min(max(fx * 0.5, dw / 2 + 0.2), fx - dw / 2 - 0.2)
    dh = min(0.95, wh - 0.2)
    swall(dcx - dw / 2 - 0.06, dcx + dw / 2 + 0.06, 0, dh + 0.05, frame)
    swall(dcx - dw / 2, dcx + dw / 2, 0, dh, _rgb("#5a3a24"))
    swall(dcx - 0.02, dcx + 0.02, 0, dh, _rgb("#3a2417"))
    swall(dcx + dw / 2 - 0.08, dcx + dw / 2 - 0.02, dh * 0.45, dh * 0.55, glow)

    # window rows (one per storey); beltcourse between floors on 2-storey
    if storeys == 2:
        rows = [wh * 0.26, wh * 0.72]
        swall(0, fx, wh * 0.5 - 0.05, wh * 0.5 + 0.05, _shade(wd, 1.0))
        ewall(0, fy, wh * 0.5 - 0.05, wh * 0.5 + 0.05, _shade(wd, 0.82))
    else:
        rows = [wh * 0.55]
    for r, zc in enumerate(rows):
        exclude = (dcx - dw / 2, dcx + dw / 2) if r == 0 else None
        for (uc, zz, w, h) in plan_windows(fx, wh, 3, exclude=exclude, zc=zc):
            draw_window(swall, uc, zz, w, h, lit=(rng.random() < 0.5))
        for (uc, zz, w, h) in plan_windows(fy, wh, 2, zc=zc):
            draw_window(ewall, uc, zz, w, h, lit=(rng.random() < 0.4))

    # flower box under the left-most front window on the ground floor
    fw = plan_windows(fx, wh, 3, exclude=(dcx - dw / 2, dcx + dw / 2), zc=rows[0])
    if fw:
        fbx, fbz = fw[0][0], fw[0][1] - fw[0][3] / 2 - 0.16
        swall(fbx - 0.28, fbx + 0.28, fbz, fbz + 0.1, _rgb("#6e4a2f"))
        for i, col in enumerate(["#d97b7b", "#e3d05a", "#e8e4dc", "#ffd982"]):
            u = fbx - 0.18 + i * 0.12
            swall(u - 0.03, u + 0.03, fbz + 0.08, fbz + 0.16, _rgb(col))

    # --- roof (ridge along y): two slopes + south gable ---
    o = 0.22
    ez = wh
    apex_x, apex_z = fx / 2, wh + rh
    ex0, ex1, ey0, ey1 = -o, fx + o, -o, fy + o
    s.poly([(ex1, ey0, ez), (ex1, ey1, ez), (apex_x, ey1, apex_z), (apex_x, ey0, apex_z)], roof_dark)
    s.poly([(ex0, ey0, ez), (ex0, ey1, ez), (apex_x, ey1, apex_z), (apex_x, ey0, apex_z)], roof_lit)
    for t in np.linspace(0.12, 0.92, 7):
        s.line((ex0 + (apex_x - ex0) * t, ey0, ez + (apex_z - ez) * t),
               (ex0 + (apex_x - ex0) * t, ey1, ez + (apex_z - ez) * t), _shade(rd0, 1.0), 1)
        s.line((ex1 + (apex_x - ex1) * t, ey0, ez + (apex_z - ez) * t),
               (ex1 + (apex_x - ex1) * t, ey1, ez + (apex_z - ez) * t), _shade(rd0, 0.8), 1)
    # south gable (plaster-ish) + vent
    s.poly([(0, fy, wh), (fx, fy, wh), (apex_x, fy, apex_z)], _shade(wb, 0.82))
    s.poly([(apex_x - 0.18, fy, wh + rh * 0.42), (apex_x + 0.18, fy, wh + rh * 0.42),
            (apex_x + 0.12, fy, wh + rh * 0.6), (apex_x - 0.12, fy, wh + rh * 0.6)], _rgb("#5a3a24"))
    s.line((apex_x, ey0, apex_z), (apex_x, ey1, apex_z), _shade(rl0, 1.15), 2)
    s.line((ex0, ey1, ez), (apex_x, ey1, apex_z), _rgb("#3a2417"), 1)
    s.line((ex1, ey1, ez), (apex_x, ey1, apex_z), _rgb("#3a2417"), 1)

    # chimney + optional smoke
    if chimney:
        chx, chy = fx * 0.72, fy * 0.3
        cz0, cz1 = wh + rh * 0.55, wh + rh * 1.15
        s.poly([(chx, chy, cz0), (chx + 0.28, chy, cz0), (chx + 0.28, chy, cz1), (chx, chy, cz1)], _rgb("#b55a33"))
        s.poly([(chx + 0.28, chy, cz0), (chx + 0.28, chy + 0.28, cz0),
                (chx + 0.28, chy + 0.28, cz1), (chx + 0.28, chy, cz1)], _shade("#b55a33", 0.8))
        s.poly([(chx - 0.04, chy - 0.04, cz1), (chx + 0.32, chy - 0.04, cz1),
                (chx + 0.32, chy + 0.32, cz1), (chx - 0.04, chy + 0.32, cz1)], _rgb("#948da3"))
        if smoke:
            for dz, dxy in [(0.25, 0.05), (0.5, 0.15), (0.8, 0.28)]:
                s.poly([(chx + 0.1 + dxy, chy + 0.1, cz1 + dz), (chx + 0.24 + dxy, chy + 0.1, cz1 + dz),
                        (chx + 0.24 + dxy, chy + 0.24, cz1 + dz + 0.12),
                        (chx + 0.1 + dxy, chy + 0.24, cz1 + dz + 0.12)], _rgb("#c8c8c0"))

    # door awning (juts toward viewer)
    s.poly([(dcx - dw / 2 - 0.12, fy, dh + 0.07), (dcx + dw / 2 + 0.12, fy, dh + 0.07),
            (dcx + dw / 2 + 0.12, fy + 0.35, dh - 0.09), (dcx - dw / 2 - 0.12, fy + 0.35, dh - 0.09)],
           _shade(rd0, 0.95))
    return s.render()


# ---- simple props ---------------------------------------------------------

def _box(s, x0, y0, z0, dx, dy, dz, hexcol):
    """Add the 3 visible faces of an axis-aligned box (top-left light)."""
    top = _shade(hexcol, 1.12)
    left = _shade(hexcol, 1.0)
    right = _shade(hexcol, 0.78)
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    s.poly([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], left)     # SW face
    s.poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], right)    # SE face
    s.poly([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], top)      # top
    return (x1, y1, z1)


def crate():
    s = Sprite()
    _box(s, 0, 0, 0, 0.7, 0.7, 0.7, "#94684a")
    s.line((0, 0.7, 0.35), (0.7, 0.7, 0.35), _rgb("#5a3a24"), 1)
    s.line((0.7, 0, 0.35), (0.7, 0.7, 0.35), _rgb("#5a3a24"), 1)
    return s.render()


def fence(axis="x", gate=False):
    """Fence segment spanning one world unit along `axis` ('x' or 'y'). With
    gate=True the rails are omitted (a gap/opening for a path)."""
    s = Sprite()
    wood, dark = "#8f5a3a", _rgb("#5a3a24")
    posts = ((0.0, 0.0), (1.0, 0.0)) if axis == "x" else ((0.0, 0.0), (0.0, 1.0))
    for px, py in posts:
        _box(s, px, py, 0, 0.14, 0.14, 1.0, wood)
    if not gate:
        for rz in (0.5, 0.85):
            if axis == "x":
                s.poly([(0.05, 0.05, rz), (1.05, 0.05, rz), (1.05, 0.05, rz + 0.12), (0.05, 0.05, rz + 0.12)],
                       _shade(wood, 1.0))
                s.line((0.05, 0.05, rz), (1.05, 0.05, rz), dark, 1)
            else:
                s.poly([(0.05, 0.05, rz), (0.05, 1.05, rz), (0.05, 1.05, rz + 0.12), (0.05, 0.05, rz + 0.12)],
                       _shade(wood, 0.9))
                s.line((0.05, 0.05, rz), (0.05, 1.05, rz), dark, 1)
    return s.render()


def firewood(seed=0):
    """Stacked firewood: a low box of logs with round ends on the front face."""
    s = Sprite()
    _box(s, 0, 0, 0, 1.0, 0.5, 0.5, "#8f5a3a")
    im, ax, ay = s.render(do_outline=True, shadow=True)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    # log-end circles on the SE face region (right side of sprite)
    for r in range(2):
        for c in range(4):
            cx = ax + 6 + c * 6
            cy = ay - 6 - r * 6 + c * 3
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=_rgb("#c4a86a"))
            d.point((cx, cy), fill=_rgb("#5a3a24"))
    return im, ax, ay


def garden_bed(seed=0):
    """Raised soil bed with rows of little sprouts (iso)."""
    s = Sprite()
    _box(s, 0, 0, 0, 1.2, 0.9, 0.16, "#6e4a2f")
    im, ax, ay = s.render(do_outline=True, shadow=True)
    d = ImageDraw.Draw(im)
    # sprout rows on the top face
    for row in range(3):
        for col in range(4):
            wx, wy = 0.15 + col * 0.28, 0.2 + row * 0.24
            sx, sy = project(wx, wy, 0.16)
            px, py = ax + sx, ay + sy
            d.line([(px, py), (px, py - 3)], fill=_rgb("#4a8f4a"))
            d.point((px, py - 4), fill=_rgb("#5fa85f"))
    return im, ax, ay


def bench():
    s = Sprite()
    for lx in (0.05, 0.85):
        _box(s, lx, 0.1, 0, 0.1, 0.1, 0.45, "#8f5a3a")
    _box(s, 0, 0, 0.45, 1.0, 0.3, 0.12, "#b0623a")
    return s.render()


def mailbox():
    s = Sprite()
    _box(s, 0.1, 0.1, 0, 0.1, 0.1, 0.9, "#6e4a2f")
    _box(s, 0, 0, 0.9, 0.35, 0.3, 0.28, "#b0453a")
    return s.render()


def well_iso():
    s = Sprite()
    _box(s, 0, 0, 0, 1.0, 1.0, 0.55, "#a8a8a0")
    s.poly([(0.15, 0.15, 0.55), (0.85, 0.15, 0.55), (0.85, 0.85, 0.55), (0.15, 0.85, 0.55)],
           _rgb("#3a3a44"))                                         # opening
    for px, py in [(0.05, 0.05), (0.85, 0.85)]:
        _box(s, px, py, 0.55, 0.1, 0.1, 1.0, "#8f5a3a")
    # roof (two slopes)
    ax = 0.5
    s.poly([(-0.1, -0.1, 1.55), (-0.1, 1.1, 1.55), (ax, 1.1, 1.9), (ax, -0.1, 1.9)], _shade("#b0453a", 1.05))
    s.poly([(1.1, -0.1, 1.55), (1.1, 1.1, 1.55), (ax, 1.1, 1.9), (ax, -0.1, 1.9)], _shade("#b0453a", 0.82))
    return s.render()


def lamp_post():
    s = Sprite()
    metal = _rgb("#565061")
    s.poly([(0, 0, 0), (0.12, 0, 0), (0.12, 0, 2.2), (0, 0, 2.2)], metal)
    s.poly([(0, 0, 2.2), (0.35, 0, 2.2), (0.35, 0, 2.35), (0, 0, 2.35)], metal)
    s.poly([(0.28, 0, 2.05), (0.42, 0, 2.05), (0.42, 0, 2.3), (0.28, 0, 2.3)], _rgb("#ffd982"))
    return s.render()


def barrel():
    s = Sprite()
    wood, dark, light = _rgb("#8f5a3a"), _rgb("#5a3a24"), _rgb("#b0623a")
    for zz in (0.0, 0.45, 0.9):
        pass
    s.poly([(0, 0, 0), (0.6, 0, 0), (0.6, 0, 0.95), (0, 0, 0.95)], wood)
    s.poly([(0, 0, 0), (0, 0.6, 0), (0, 0.6, 0.95), (0, 0, 0.95)], light)
    s.line((0, 0, 0.5), (0.6, 0, 0.5), dark, 1)
    return s.render()


def _billboard(draw_fn, w, h, base_x, base_y, shadow_r=0):
    """Camera-facing sprite drawn directly in screen space. Anchor = base point.
    draw_fn(ImageDraw) draws into a (w,h) canvas; returns (im, ax, ay)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow_r:
        d.ellipse([base_x - shadow_r, base_y - shadow_r // 3, base_x + shadow_r, base_y + shadow_r // 3],
                  fill=(0, 0, 0, 55))
    draw_fn(d)
    im = quantize(im)
    im = outline(im, OUTLINE)
    return im, base_x, base_y


def bush(seed=1):
    def draw(d):
        for dx, dy, r, c in [(-7, 4, 9, "#3e6631"), (7, 4, 9, "#5fa85f"), (0, 0, 11, "#4a8f4a")]:
            d.ellipse([20 + dx - r, 18 + dy - r, 20 + dx + r, 18 + dy + r], fill=_rgb(c))
        d.ellipse([13, 8, 21, 14], fill=_rgb("#5fa85f"))
    return _billboard(draw, 40, 30, 20, 27, shadow_r=12)


# --- deciduous species: (dark, mid, base, light), trunk, shape, trunk_w ---
TREE_SPECIES = {
    "oak":    (("#2f5a2b", "#446a32", "#4a8f4a", "#5f8f46"), "#6e4a2f", "round", 6),
    "maple":  (("#8f4f2f", "#b0623a", "#cc7444", "#e3d05a"), "#5a3a24", "round", 6),
    "birch":  (("#446a32", "#5f8f46", "#7cc45e", "#e3d05a"), "#e8e4dc", "tall", 4),
    "poplar": (("#345527", "#3e6631", "#4a7a3a", "#5f8f46"), "#6e4a2f", "column", 4),
    "linden": (("#4a7a3a", "#5f8f46", "#7cc45e", "#e3d05a"), "#7a5238", "round", 6),
}
CONIFER_SPECIES = {
    "spruce": (("#243f22", "#2f5a2b", "#345527"), 4, 78),
    "pine":   (("#2f5a2b", "#345527", "#446a32"), 3, 86),
    "fir":    (("#345527", "#3e6631", "#446a32"), 5, 74),
}


def tree(species="oak", seed=0):
    """Deciduous tree billboard; species sets colour + canopy shape.
    Slight per-seed jitter so no two are identical."""
    (dk, md, bs, lt), trunk, shape, tw = TREE_SPECIES.get(species, TREE_SPECIES["oak"])
    rng = np.random.default_rng(seed)
    jx = int(rng.integers(-2, 3))

    def draw(d):
        cx = 30
        if shape == "column":  # tall narrow poplar/cypress crown
            d.rectangle([cx - tw // 2, 52, cx + tw // 2, 68], fill=_rgb(trunk))
            d.ellipse([cx - 11 + jx, 6, cx + 11 + jx, 56], fill=_rgb(dk))
            d.ellipse([cx - 9 + jx, 8, cx + 9 + jx, 54], fill=_rgb(bs))
            d.ellipse([cx - 8 + jx, 10, cx + 3 + jx, 44], fill=_rgb(md))
            d.ellipse([cx - 7 + jx, 12, cx - 1 + jx, 34], fill=_rgb(lt))
        elif shape == "tall":
            d.rectangle([cx - tw // 2, 42, cx + tw // 2, 68], fill=_rgb(trunk))
            if species == "birch":
                for ty in (48, 55, 62):
                    d.line([(cx - tw // 2, ty), (cx + tw // 2, ty)], fill=_rgb("#565061"))
            for dx, dy, r, c in [(-7, 10, 11, dk), (7, 12, 10, md), (0, -2, 14, bs), (-3, -8, 9, lt)]:
                d.ellipse([cx + dx - r + jx, 24 + dy - r, cx + dx + r + jx, 24 + dy + r], fill=_rgb(c))
        else:  # round
            d.rectangle([cx - tw // 2, 44, cx + tw // 2, 66], fill=_rgb(trunk))
            d.rectangle([cx - tw // 2, 44, cx - tw // 2 + 2, 66], fill=_rgb("#8f5a3a"))
            for dx, dy, r, c in [(-12, 6, 15, dk), (12, 8, 14, md), (0, -2, 19, bs),
                                 (-6, -8, 12, lt), (8, -4, 11, lt)]:
                d.ellipse([cx + dx - r + jx, 26 + dy - r, cx + dx + r + jx, 26 + dy + r], fill=_rgb(c))
    return _billboard(draw, 64, 72, 30, 66, shadow_r=16)


def conifer(species="spruce", seed=0):
    """Coniferous tree; species sets colour, tier count, height."""
    (dk, md, lt), tiers, h = CONIFER_SPECIES.get(species, CONIFER_SPECIES["spruce"])
    def draw(d):
        cx = 27
        d.rectangle([cx - 2, h - 12, cx + 2, h - 2], fill=_rgb("#5a3a24"))
        span = h - 14
        for i in range(tiers):
            base_y = h - 6 - int(span * i / tiers)
            half = 20 - i * (16 // max(1, tiers))
            top = base_y - int(span / tiers) - 8
            d.polygon([(cx, top), (cx - half, base_y), (cx + half, base_y)], fill=_rgb(md))
            d.polygon([(cx, top), (cx - half, base_y), (cx - int(half * 0.35), base_y)], fill=_rgb(lt))
            d.line([(cx, top), (cx - half, base_y)], fill=_rgb(dk))
            d.line([(cx, top), (cx + half, base_y)], fill=_rgb(dk))
    return _billboard(draw, 58, h + 4, 27, h - 2, shadow_r=13)


# ---- animated elements (frames baked; sway/flicker via engine) ------------

def smoke_plume(frame=0, nframes=6, seed=0):
    """Rising chimney smoke (loops over nframes). Anchor = bottom (chimney top)."""
    import math
    W, H = 30, 46
    greys = ["#948da3", "#a8a8a0", "#c8c8c0", "#e8e4dc"]

    def draw(d):
        cx = W // 2
        for k in range(5):
            t = ((k / 5.0) + frame / nframes) % 1.0
            y = H - 4 - t * (H - 8)
            r = 2 + t * 5
            x = cx + math.sin(t * 6.28 + k) * 4 * t
            c = greys[min(3, int(t * 4))]
            d.ellipse([x - r, y - r, x + r, y + r], fill=_rgb(c))
    return _billboard(draw, W, H, W // 2, H - 2, shadow_r=0)


def campfire(frame=0, nframes=6, seed=0):
    """Camp fire with flickering flame + log base + stone ring. Loops."""
    import math
    W, H = 40, 40

    def draw(d):
        cx, base = W // 2, H - 6
        for a in range(0, 360, 60):  # stone ring
            sx = cx + int(11 * math.cos(math.radians(a)))
            sy = base + int(5 * math.sin(math.radians(a)))
            d.ellipse([sx - 3, sy - 2, sx + 3, sy + 2], fill=_rgb("#7a7485"))
        d.line([(cx - 8, base), (cx + 8, base - 3)], fill=_rgb("#5a3a24"), width=3)  # logs
        d.line([(cx - 8, base - 3), (cx + 8, base)], fill=_rgb("#6e4a2f"), width=3)
        f = frame / nframes * 6.28
        h1 = 12 + int(3 * math.sin(f))
        h2 = 8 + int(3 * math.sin(f + 2))
        d.polygon([(cx, base - h1), (cx - 5, base - 2), (cx + 5, base - 2)], fill=_rgb("#cc6452"))
        d.polygon([(cx + int(2 * math.sin(f)), base - h2), (cx - 3, base - 2), (cx + 4, base - 2)],
                  fill=_rgb("#e8c15a"))
        d.polygon([(cx, base - h2 // 2 - 2), (cx - 2, base - 2), (cx + 2, base - 2)], fill=_rgb("#ffd982"))
    return _billboard(draw, W, H, W // 2, H - 2, shadow_r=10)


def glow(frame=0, nframes=4, seed=0, color="#ffd982"):
    """Small warm flicker (window/lamp light) — brightness pulses. Anchor centre."""
    import math
    W = H = 12
    lvl = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(frame / nframes * 6.28))

    def draw(d):
        c = _shade(color, lvl)
        d.ellipse([2, 2, W - 2, H - 2], fill=c)
        d.ellipse([4, 4, W - 5, H - 5], fill=_shade("#ffffff" if False else "#e8e4dc", lvl))
    return _billboard(draw, W, H, W // 2, H // 2, shadow_r=0)


def pack_sheet(frames):
    """Pack equal-size frame sprites into one horizontal strip. `frames` is a
    list of (image, ax, ay); returns (sheet_image, frame_w, frame_h, anchor)."""
    ims = [f[0] for f in frames]
    fw = max(im.size[0] for im in ims)
    fh = max(im.size[1] for im in ims)
    sheet = Image.new("RGBA", (fw * len(ims), fh), (0, 0, 0, 0))
    for k, (im, ax, ay) in enumerate(frames):
        sheet.alpha_composite(im, (k * fw + (fw - im.size[0]) // 2, fh - im.size[1]))
    return sheet, fw, fh


def rock(seed=0):
    def draw(d):
        base, dark, light = _rgb("#7a7485"), _rgb("#565061"), _rgb("#948da3")
        d.ellipse([6, 14, 30, 28], fill=dark)
        d.ellipse([6, 11, 30, 24], fill=base)
        d.ellipse([9, 12, 22, 19], fill=light)
    return _billboard(draw, 38, 32, 18, 26, shadow_r=11)


def flowers(seed=0):
    def draw(d):
        rng = np.random.default_rng(seed)
        cols = ["#d97b7b", "#e3d05a", "#e8e4dc", "#ffd982", "#cc6452"]
        for _ in range(6):
            x, y = int(rng.integers(4, 24)), int(rng.integers(10, 22))
            d.line([(x, y + 4), (x, y)], fill=_rgb("#446a32"))
            d.point((x, y - 1), fill=_rgb(cols[int(rng.integers(len(cols)))]))
    return _billboard(draw, 28, 26, 14, 22, shadow_r=0)


def stump(seed=0):
    def draw(d):
        wood, dark, light = _rgb("#8f5a3a"), _rgb("#5a3a24"), _rgb("#c4a86a")
        d.rectangle([10, 14, 26, 24], fill=wood)
        d.ellipse([10, 10, 26, 18], fill=light)
        d.ellipse([14, 12, 22, 16], fill=dark)
    return _billboard(draw, 36, 28, 18, 24, shadow_r=10)


def log(seed=0):
    def draw(d):
        wood, dark, light = _rgb("#8f5a3a"), _rgb("#5a3a24"), _rgb("#c4a86a")
        d.rectangle([4, 12, 34, 20], fill=wood)
        d.ellipse([2, 12, 8, 20], fill=light)
        d.ellipse([3, 13, 7, 19], fill=dark)
        d.ellipse([31, 12, 37, 20], fill=dark)
    return _billboard(draw, 40, 26, 20, 22, shadow_r=10)
