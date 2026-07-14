#!/usr/bin/env python3
"""Iso world composer (Stage 5): assembles biomes + an organic-edged lake +
roads + a small lakeside village + scattered flora into one depth-sorted map.
Run: python scripts/iso_world.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402
from artgen.canvas import value_noise  # noqa: E402

OX, OY = 720, 70
GW, GH = 24, 18
SEED = 5


def build():
    rng = np.random.default_rng(SEED)
    # organic lake mask at CORNER resolution (GW+1 x GH+1): ellipse + noise wobble
    wob = value_noise(GW + 1, GH + 1, seed=SEED + 2, octaves=3, base_freq=4)
    LC = np.zeros((GH + 1, GW + 1), bool)
    for jj in range(GH + 1):
        for ii in range(GW + 1):
            e = ((ii - 15.5) / 6.0) ** 2 + ((jj - 12.0) / 4.2) ** 2
            LC[jj, ii] = (e + (wob[jj, ii] - 0.5) * 0.9) < 1.0

    def biome(i, j):
        if i + j < 6:
            return "sand"
        if i >= 17 and j <= 6:
            return "forest_floor"
        if ((i - 5) / 3.5) ** 2 + ((j - 4) / 2.6) ** 2 <= 1:
            return "meadow"
        return "grass"

    path_cells = set()
    homesteads = [dict(ox=2, oy=8, walls="log", roof="red", seed=1, door_x=4, st=1),
                  dict(ox=8, oy=9, walls="plaster", roof="slate", seed=2, door_x=10, st=2)]
    road_row = 7
    for h in homesteads:
        for j in range(h["oy"] + 4, road_row - 1, -1):
            path_cells.add((h["door_x"], j))

    def is_road(i, j):
        return j == road_row and i <= 13

    scene = Image.new("RGBA", (1500, 1080), (0, 0, 0, 0))
    edge_nb = {"SE": (1, 0), "NW": (-1, 0), "SW": (0, 1), "NE": (0, -1)}
    B = [[biome(i, j) for i in range(GW)] for j in range(GH)]

    def bat(i, j):
        return B[j][i] if 0 <= i < GW and 0 <= j < GH else "grass"

    for j in range(GH):
        for i in range(GW):
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            corners = (LC[j, i], LC[j, i + 1], LC[j + 1, i + 1], LC[j + 1, i])
            if any(corners):
                tile = iso.coast_tile(corners, seed=i * 9 + j * 5, land_kind=bat(i, j))
            elif is_road(i, j) or (i, j) in path_cells:
                fr = {e for e, (di, dj) in edge_nb.items()
                      if not (is_road(i + di, j + dj) or (i + di, j + dj) in path_cells)}
                tile = iso.diamond("path", seed=i * 13 + j * 7, world=(i, j), fringe=fr)
            else:
                k = bat(i, j)
                fr = {e for e, (di, dj) in edge_nb.items()
                      if k != "grass" and bat(i + di, j + dj) in ("grass", "meadow")}
                tile = iso.diamond(k, seed=i * 13 + j * 7, world=(i, j), fringe=fr)
            scene.alpha_composite(tile, pos)

    objs = []

    def add(sp, wx, wy, foot=(0, 0), z=0):
        im, ax, ay = sp
        objs.append(((wx + foot[0]) + (wy + foot[1]) + z * 1e-3, im, ax, ay, wx, wy))

    # village
    for h in homesteads:
        ox, oy = h["ox"], h["oy"]
        add(iso.house(h["walls"], h["roof"], fx=2.0, fy=2.0, storeys=h["st"],
                      seed=h["seed"], smoke=(h["seed"] % 2 == 1)), ox + 1, oy + 1, foot=(2, 2), z=1)
        x0, y0, x1, y1 = ox, oy, ox + 4, oy + 4
        for x in range(x0, x1):
            add(iso.fence("x"), x, y0)
            add(iso.fence("x", gate=(x == h["door_x"])), x, y1)
        for y in range(y0, y1):
            add(iso.fence("y"), x0, y)
            add(iso.fence("y"), x1, y)
        add(iso.garden_bed(h["seed"]), x0 + 0.2, y0 + 0.3)
        add(iso.firewood(h["seed"]), x1 - 1.1, y0 + 0.2)
        add(iso.well_iso(), x1 - 1.2, y1 - 1.4, foot=(1, 1))
        add(iso.lamp_post(), h["door_x"] + 0.6, y1 + 0.1, z=1)
        add(iso.tree(list(iso.TREE_SPECIES)[h["seed"] % 5], h["seed"]), x0 - 0.4, y0 - 0.4, z=1)
    add(iso.campfire(0), 6.5, 11.0, z=1)

    # lakeside plants + boat (place on shore/water cells)
    add(iso.reeds_patch(2), 11.5, 9.4)
    add(iso.lily_pads(3), 15.0, 12.0)
    add(iso.boat(0), 16.0, 11.5, z=1)

    # scattered flora on land
    for _ in range(40):
        i, j = int(rng.integers(0, GW)), int(rng.integers(0, GH))
        if any((LC[j, i], LC[j, i + 1], LC[j + 1, i + 1], LC[j + 1, i])):
            continue
        k = B[j][i]
        r = rng.random()
        if k == "forest_floor":
            fn = (iso.tree(list(iso.TREE_SPECIES)[int(rng.integers(5))], i + j) if r < 0.5
                  else iso.conifer(list(iso.CONIFER_SPECIES)[int(rng.integers(3))], i + j))
            add(fn, i + 0.5, j + 0.5, z=1)
        elif k in ("grass", "meadow") and r < 0.5:
            if r < 0.15:
                add(iso.tree("oak", i + j), i + 0.5, j + 0.5, z=1)
            elif r < 0.3:
                add(iso.bush(), i + 0.5, j + 0.5)
            elif r < 0.42:
                add(iso.flowers(i + j), i + 0.5, j + 0.5)
            else:
                add(iso.rock(i + j), i + 0.5, j + 0.5)

    for depth, im, ax, ay, wx, wy in sorted(objs, key=lambda t: t[0]):
        sx, sy = iso.project(wx, wy, 0)
        scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    bbox = scene.getbbox()
    if bbox:
        m = 18
        scene = scene.crop((max(0, bbox[0] - m), max(0, bbox[1] - m),
                            min(scene.size[0], bbox[2] + m), min(scene.size[1], bbox[3] + m)))
    bg = Image.new("RGBA", scene.size, (58, 58, 68, 255))
    bg.alpha_composite(scene)
    return bg


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    sc = build()
    sc.save(os.path.join(out, "iso_world.png"))
    sc.resize((int(sc.size[0] * 1.5), int(sc.size[1] * 1.5)), Image.NEAREST).save(
        os.path.join(out, "iso_world_1_5x.png"))
    print("wrote iso_world.png", sc.size)
