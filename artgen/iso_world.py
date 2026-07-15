"""Parametric iso world composer — «красивая карта» одним вызовом.

compose(seed, gw, gh, houses, lake, forest) собирает деревню: сеть дорог,
дворы с домами/заборами/огородами, фонари вдоль улиц, колодцы, поленницы,
плотную флору по биомам, озеро с камышом и лодкой. Всё детерминировано по
seed. Возвращает (PIL.Image, manifest dict).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import iso
from .canvas import value_noise

_EDGE_NB = {"SE": (1, 0), "NW": (-1, 0), "SW": (0, 1), "NE": (0, -1)}


def _lake_mask(gw, gh, seed, enabled):
    LC = np.zeros((gh + 1, gw + 1), bool)
    if not enabled:
        return LC
    rng = np.random.default_rng(seed + 11)
    cx = gw * (0.62 + rng.random() * 0.2)
    cy = gh * (0.55 + rng.random() * 0.25)
    rx, ry = gw * 0.16 + rng.random() * 2, gh * 0.14 + rng.random() * 1.5
    wob = value_noise(gw + 1, gh + 1, seed=seed + 2, octaves=3, base_freq=4)
    for j in range(gh + 1):
        for i in range(gw + 1):
            e = ((i - cx) / rx) ** 2 + ((j - cy) / ry) ** 2
            LC[j, i] = (e + (wob[j, i] - 0.5) * 0.9) < 1.0
    return LC


def compose(seed=1, gw=26, gh=20, houses=4, lake=True, forest=0.5,
            forest_ring=0, scale=1):
    """forest_ring>0 — опушка: лес полосой такой ширины по периметру карты
    (дорога прорубает её и уходит с карты «в город»)."""
    rng = np.random.default_rng(seed)
    LC = _lake_mask(gw, gh, seed, lake)

    def wet(i, j):
        return (LC[j, i] or LC[j, i + 1] or LC[j + 1, i + 1] or LC[j + 1, i])

    # biome zones: meadow blobs + forest band by noise
    zn = value_noise(gw, gh, seed=seed + 5, octaves=3, base_freq=3)
    t_forest = float(np.quantile(zn, 1.0 - 0.28 * forest * 2))  # доля площади под лес
    t_meadow = float(np.quantile(zn, 0.16))
    B = [["grass" for _ in range(gw)] for _ in range(gh)]
    ring_noise = value_noise(gw, gh, seed=seed + 9, octaves=2, base_freq=5)
    for j in range(gh):
        for i in range(gw):
            if zn[j, i] >= t_forest:
                B[j][i] = "forest_floor"
            elif zn[j, i] <= t_meadow:
                B[j][i] = "meadow"
            if forest_ring:
                edge = min(i, j, gw - 1 - i, gh - 1 - j)
                if edge < forest_ring + (ring_noise[j, i] - 0.5) * 2.2:
                    B[j][i] = "forest_floor"

    # road: main horizontal street + vertical branch per house
    road_row = int(gh * 0.42)
    roads = set()
    yards = []          # (x0,y0) of 4x4 yards
    tries = 0
    m = max(1, forest_ring)
    while len(yards) < houses and tries < 300:
        tries += 1
        x0 = int(rng.integers(m, max(m + 1, gw - 5 - m)))
        y0 = int(rng.integers(m, max(m + 1, gh - 5 - m)))
        if forest_ring and any(B[y][x] == "forest_floor"
                               for x in range(x0, x0 + 5)
                               for y in range(y0, y0 + 5)):
            continue
        if abs(y0 + 2 - road_row) < 2:
            continue
        box = [(x, y) for x in range(x0 - 1, x0 + 6) for y in range(y0 - 1, y0 + 6)]
        if any(not (0 <= x < gw and 0 <= y < gh) or wet(x, y) for x, y in box):
            continue
        gap = 6 if min(gw, gh) - 2 * m >= 16 else 5
        if any(abs(x0 - vx) < gap and abs(y0 - vy) < gap for vx, vy in yards):
            continue
        yards.append((x0, y0))
    for x in range(0, gw):     # дорога прорубает опушку и уходит с карты
        if not wet(x, road_row):
            roads.add((x, road_row))
    hmeta = []
    for n, (x0, y0) in enumerate(yards):
        door_x = x0 + 2
        step = -1 if y0 > road_row else 1
        for y in range(y0 + (4 if step == -1 else 0), road_row, step):
            if not wet(door_x, y):
                roads.add((door_x, y))
        walls = ["log", "timber", "plaster", "stone"][n % 4]
        roof = ["thatch", "green", "red", "slate"][int(rng.integers(4))]
        st = 1 + int(rng.random() < 0.4)
        hmeta.append(dict(x0=x0, y0=y0, door_x=door_x, walls=walls, roof=roof,
                          st=st, seed=seed * 7 + n))

    def is_road(i, j):
        return (i, j) in roads

    # ---- ground pass
    W = (gw + gh) * iso.HW + 4 * iso.HW
    H = (gw + gh) * iso.HH + 240
    OX, OY = gh * iso.HW + 2 * iso.HW, 90
    scene = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame_all = 0
    for j in range(gh):
        for i in range(gw):
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            corners = (LC[j, i], LC[j, i + 1], LC[j + 1, i + 1], LC[j + 1, i])
            if any(corners):
                tile = iso.coast_tile(corners, seed=i * 9 + j * 5, frame=frame_all,
                                      land_kind=B[j][i])
            elif is_road(i, j):
                fr = {e for e, (di, dj) in _EDGE_NB.items()
                      if not is_road(i + di, j + dj)}
                tile = iso.diamond("path", seed=i * 13 + j * 7, world=(i, j), fringe=fr)
            else:
                k = B[j][i]
                fr = {e for e, (di, dj) in _EDGE_NB.items()
                      if k != "grass" and B[min(max(j + dj, 0), gh - 1)][min(max(i + di, 0), gw - 1)] == "grass"}
                tile = iso.diamond(k, seed=i * 13 + j * 7, world=(i, j), fringe=fr)
            scene.alpha_composite(tile, pos)

    # ---- objects
    objs = []

    def add(sp, wx, wy, foot=(0, 0), z=0):
        im, ax, ay = sp
        objs.append(((wx + foot[0]) + (wy + foot[1]) + z * 1e-3, im, ax, ay, wx, wy))

    occupied = set(roads)
    for h in hmeta:
        x0, y0 = h["x0"], h["y0"]
        add(iso.house(h["walls"], h["roof"], fx=2.0, fy=2.0, storeys=h["st"],
                      seed=h["seed"], smoke=bool(h["seed"] % 2)),
            x0 + 1, y0 + 1, foot=(2, 2), z=1)
        x1, y1 = x0 + 4, y0 + 4
        gate_side_y = y1 if y0 < 20 else y0
        for x in range(x0, x1):
            add(iso.fence("x"), x, y0)
            add(iso.fence("x", gate=(x == h["door_x"])), x, y1)
        for y in range(y0, y1):
            add(iso.fence("y"), x0, y)
            add(iso.fence("y"), x1, y)
        add(iso.garden_bed(h["seed"]), x0 + 0.2, y0 + 0.25)
        add(iso.garden_bed(h["seed"] + 1), x0 + 0.2, y0 + 1.1)
        add(iso.firewood(h["seed"]), x1 - 1.1, y0 + 0.2)
        add(iso.barrel(), x1 - 0.5, y0 + 0.9)
        if h["seed"] % 3 == 0:
            add(iso.well_iso(), x1 - 1.2, y1 - 1.4, foot=(1, 1))
        add(iso.lamp_post(), h["door_x"] + 0.6, y1 + 0.15, z=1)
        add(iso.bush(h["seed"]), x0 - 0.4, y1 + 0.3)
        add(iso.tree(list(iso.TREE_SPECIES)[h["seed"] % 5], h["seed"]),
            x0 - 0.5, y0 - 0.5, z=1)
        for x in range(x0 - 1, x1 + 2):
            for y in range(y0 - 1, y1 + 2):
                occupied.add((x, y))

    # street lamps + benches along the main road
    for x in range(2, gw - 2, 5):
        if (x, road_row) in roads and not wet(x, road_row + 1):
            add(iso.lamp_post(), x + 0.5, road_row + 1.2, z=1)
            occupied.add((x, road_row + 1))
    add(iso.campfire(frame_all), *(np.array(yards[0][:2]) + (5.5, 5.5))
        if yards else (2.5, 2.5), z=1)

    # lakeside
    if lake and LC.any():
        js, is_ = np.where(LC[:-1, :-1])
        pick = rng.integers(len(js), size=min(4, len(js)))
        shore = list(zip(is_[pick], js[pick]))
        if shore:
            add(iso.reeds_patch(2), shore[0][0] + 0.5, shore[0][1] + 0.4)
            if len(shore) > 1:
                add(iso.lily_pads(3), shore[1][0] + 0.5, shore[1][1] + 0.5)
            ci, cj = int(np.mean(is_)), int(np.mean(js))
            add(iso.boat(frame_all), ci + 0.3, cj + 0.3, z=1)

    # dense flora scatter
    for _ in range(int(gw * gh * 0.3)):
        i, j = int(rng.integers(0, gw)), int(rng.integers(0, gh))
        if wet(i, j) or (i, j) in occupied:
            continue
        k = B[j][i]
        r = rng.random()
        wx, wy = i + 0.2 + rng.random() * 0.6, j + 0.2 + rng.random() * 0.6
        if k == "forest_floor":
            # роща: 2-4 дерева пучком на клетку
            for _ in range(2 + int(rng.integers(3))):
                ox, oy = rng.random() * 0.9 - 0.45, rng.random() * 0.9 - 0.45
                rr = rng.random()
                if rr < 0.55:
                    add(iso.tree(list(iso.TREE_SPECIES)[int(rng.integers(5))],
                                 int(rng.integers(99))), wx + ox, wy + oy, z=1)
                else:
                    add(iso.conifer(list(iso.CONIFER_SPECIES)[int(rng.integers(3))],
                                    int(rng.integers(99))), wx + ox, wy + oy, z=1)
            if r > 0.85:
                add(iso.stump(int(rng.integers(99))), wx, wy)
        elif k == "meadow":
            if r < 0.5:
                add(iso.flowers(int(rng.integers(99))), wx, wy)
            elif r < 0.75:
                add(iso.bush(int(rng.integers(99))), wx, wy)
            else:
                add(iso.rock(int(rng.integers(99))), wx, wy)
        else:
            if r < 0.25:
                add(iso.tree("oak" if r < 0.12 else "linden",
                             int(rng.integers(99))), wx, wy, z=1)
            elif r < 0.45:
                add(iso.bush(int(rng.integers(99))), wx, wy)
            elif r < 0.6:
                add(iso.flowers(int(rng.integers(99))), wx, wy)
            elif r < 0.72:
                add(iso.rock(int(rng.integers(99))), wx, wy)
            elif r < 0.82:
                add(iso.log(int(rng.integers(99))), wx, wy)

    for depth, im, ax, ay, wx, wy in sorted(objs, key=lambda t: t[0]):
        sx, sy = iso.project(wx, wy, 0)
        scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    bbox = scene.getbbox()
    if bbox:
        m = 18
        scene = scene.crop((max(0, bbox[0] - m), max(0, bbox[1] - m),
                            min(scene.size[0], bbox[2] + m),
                            min(scene.size[1], bbox[3] + m)))
    bg = Image.new("RGBA", scene.size, (35, 27, 4, 255))
    bg.alpha_composite(scene)
    if scale != 1:
        bg = bg.resize((int(bg.size[0] * scale), int(bg.size[1] * scale)),
                       Image.NEAREST)
    manifest = {"seed": seed, "grid": [gw, gh], "road_row": road_row,
                "houses": hmeta, "lake": bool(lake and LC.any())}
    return bg, manifest
