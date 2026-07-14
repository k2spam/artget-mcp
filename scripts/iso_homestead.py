#!/usr/bin/env python3
"""Iso homesteads (Stage 3): fenced yards, a narrow path to each door, gardens,
firewood, well, and houses of varied materials on grass by a road.
Run: python scripts/iso_homestead.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402

OX, OY = 640, 90
GW, GH = 20, 15
ROAD_ROWS = (11, 12)


def build():
    scene = Image.new("RGBA", (1320, 900), (0, 0, 0, 0))
    path_cells = set()

    homesteads = [
        dict(ox=1, oy=2, walls="log", roof="red", seed=1, door_x=3),
        dict(ox=8, oy=2, walls="plaster", roof="slate", seed=2, door_x=10),
        dict(ox=14, oy=3, walls="stone", roof="thatch", seed=3, door_x=16),
    ]
    # yard path columns from each door down to the road
    for h in homesteads:
        for j in range(h["oy"] + 4, ROAD_ROWS[0] + 1):
            path_cells.add((h["door_x"], j))

    def is_road(i, j):
        return j in ROAD_ROWS

    # ground
    edge_nb = {"SE": (1, 0), "NW": (-1, 0), "SW": (0, 1), "NE": (0, -1)}
    for j in range(GH):
        for i in range(GW):
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            if is_road(i, j) or (i, j) in path_cells:
                fr = {e for e, (di, dj) in edge_nb.items()
                      if not (is_road(i + di, j + dj) or (i + di, j + dj) in path_cells)}
                tile = iso.diamond("path", seed=i * 13 + j * 7, world=(i, j), fringe=fr, fringe_kind="grass")
            else:
                tile = iso.diamond("grass", seed=i * 13 + j * 7, world=(i, j))
            scene.alpha_composite(tile, pos)

    objs = []

    def add(sprite_tuple, wx, wy, foot=(0, 0)):
        im, ax, ay = sprite_tuple
        objs.append(((wx + foot[0]) + (wy + foot[1]), im, ax, ay, wx, wy))

    rng = np.random.default_rng(7)
    for h in homesteads:
        ox, oy = h["ox"], h["oy"]
        x0, y0, x1, y1 = ox, oy, ox + 4, oy + 4          # yard bounds
        gate_x = h["door_x"]
        # house (footprint 2x2), front (SW) faces +y toward the road
        add(iso.house(h["walls"], h["roof"], fx=2.0, fy=2.0, seed=h["seed"],
                      smoke=(h["seed"] % 2 == 1)), ox + 1, oy + 1, foot=(2.0, 2.0))
        # fence perimeter (gate gap on the front row at the path column)
        for x in range(x0, x1):
            add(iso.fence("x"), x, y0)                                  # back
            add(iso.fence("x", gate=(x == gate_x)), x, y1)              # front (gate)
        for y in range(y0, y1):
            add(iso.fence("y"), x0, y)                                  # left
            add(iso.fence("y"), x1, y)                                  # right
        # yard decor
        add(iso.garden_bed(h["seed"]), x0 + 0.2, y0 + 0.3)
        add(iso.firewood(h["seed"]), x1 - 1.1, y0 + 0.2)
        add(iso.well_iso(), x1 - 1.2, y1 - 1.4, foot=(1, 1))
        add(iso.barrel(), gate_x - ox + x0 - 1.0, y1 - 0.6)
        add(iso.potted_plant() if hasattr(iso, "potted_plant") else iso.bush(), ox + 0.6, y1 - 0.5)
        add(iso.lamp_post(), gate_x + 0.6, y1 + 0.1)
        add(iso.tree(list(iso.TREE_SPECIES)[h["seed"] % 5], h["seed"]), x0 - 0.4, y0 - 0.4)
        add(iso.bush(), x1 - 0.3, y0 + 1.5)

    # a couple of roadside trees
    add(iso.tree("oak", 9), 5.5, 13.5)
    add(iso.conifer("spruce", 4), 12.5, 1.0)
    add(iso.tree("maple", 2), 19.0, 8.0)

    for depth, im, ax, ay, wx, wy in sorted(objs, key=lambda t: t[0]):
        sx, sy = iso.project(wx, wy, 0)
        scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    bbox = scene.getbbox()
    if bbox:
        m = 16
        scene = scene.crop((max(0, bbox[0] - m), max(0, bbox[1] - m),
                            min(scene.size[0], bbox[2] + m), min(scene.size[1], bbox[3] + m)))
    bg = Image.new("RGBA", scene.size, (58, 58, 68, 255))
    bg.alpha_composite(scene)
    return bg


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    sc = build()
    sc.save(os.path.join(out, "iso_homestead.png"))
    sc.resize((sc.size[0] * 2, sc.size[1] * 2), Image.NEAREST).save(os.path.join(out, "iso_homestead_2x.png"))
    print("wrote iso_homestead.png", sc.size)
