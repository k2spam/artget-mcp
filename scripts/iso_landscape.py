#!/usr/bin/env python3
"""Iso landscape demo (Stage 1): biomes (meadow/grass/forest/sand) + a lake with
foam shoreline, reeds/lilies/algae, and a bobbing boat. Run:
    python scripts/iso_landscape.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402

OX, OY = 560, 120
GW, GH = 15, 13
FRAME = 0  # single frame of the animated water/boat

_EDGE_NB = {"SE": (1, 0), "NW": (-1, 0), "SW": (0, 1), "NE": (0, -1)}

TREE_SP = list(iso.TREE_SPECIES)
CONIF_SP = list(iso.CONIFER_SPECIES)


def biome(i, j):
    if ((i - 10) / 4.2) ** 2 + ((j - 8) / 3.2) ** 2 <= 1:
        return "water"
    if i + j < 5:                                  # sand corner (top-left)
        return "sand"
    if i >= 9 and j <= 4:                          # forest patch (top-right)
        return "forest_floor"
    if ((i - 3) / 3.0) ** 2 + ((j - 8) / 2.6) ** 2 <= 1:   # meadow blob (bottom-left)
        return "meadow"
    return "grass"


GRASSY = ("grass", "meadow")


def build():
    scene = Image.new("RGBA", (1180, 820), (0, 0, 0, 0))
    B = [[biome(i, j) for i in range(GW)] for j in range(GH)]

    def bat(i, j):
        return B[j][i] if 0 <= i < GW and 0 <= j < GH else "grass"

    for j in range(GH):
        for i in range(GW):
            k = B[j][i]
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            if k == "water":
                land = {e for e, (di, dj) in _EDGE_NB.items() if bat(i + di, j + dj) != "water"}
                tile = iso.water_tile(FRAME, seed=i * 9 + j * 5, foam=land)
            elif k in ("sand", "forest_floor", "dirt", "stone"):
                # grass creeps in on edges bordering grass/meadow -> soft border
                fr = {e for e, (di, dj) in _EDGE_NB.items() if bat(i + di, j + dj) in GRASSY}
                tile = iso.diamond(k, seed=i * 13 + j * 7, world=(i, j), fringe=fr, fringe_kind="grass")
            else:
                tile = iso.diamond(k, seed=i * 13 + j * 7, world=(i, j))
            scene.alpha_composite(tile, pos)

    objs = []

    def add(sprite_tuple, wx, wy, foot=(0, 0)):
        im, ax, ay = sprite_tuple
        objs.append(((wx + foot[0]) + (wy + foot[1]), im, ax, ay, wx, wy))

    rng = np.random.default_rng(3)
    # dense mixed forest on forest_floor tiles (varied species + colours)
    for j in range(GH):
        for i in range(GW):
            if B[j][i] == "forest_floor" and rng.random() < 0.8:
                wx, wy = i + rng.random() * 0.6, j + rng.random() * 0.6
                sd = i * 31 + j
                if rng.random() < 0.5:
                    add(iso.tree(TREE_SP[int(rng.integers(len(TREE_SP)))], sd), wx, wy)
                else:
                    add(iso.conifer(CONIF_SP[int(rng.integers(len(CONIF_SP)))], sd), wx, wy)
            elif B[j][i] == "forest_floor" and rng.random() < 0.3:
                add(iso.stump(i + j) if rng.random() < 0.5 else iso.log(i + j),
                    i + rng.random() * 0.6, j + rng.random() * 0.6)

    # scattered detail on grass/meadow: lone trees, bushes, rocks, flowers
    for _ in range(16):
        i, j = int(rng.integers(0, GW)), int(rng.integers(0, GH))
        if B[j][i] in ("grass", "meadow"):
            r = rng.random()
            if r < 0.3:
                add(iso.tree(TREE_SP[int(rng.integers(len(TREE_SP)))], i * 7 + j), i + 0.5, j + 0.5)
            elif r < 0.55:
                add(iso.bush(), i + 0.5, j + 0.5)
            elif r < 0.75:
                add(iso.flowers(i * 3 + j), i + 0.5, j + 0.5)
            else:
                add(iso.rock(i + j), i + 0.5, j + 0.5)

    # lakeside plants + a boat
    add(iso.reeds_patch(2), 7.6, 6.4)
    add(iso.reeds_patch(5), 8.4, 10.6)
    add(iso.lily_pads(3), 10.5, 8.5)
    add(iso.algae(4), 12.0, 7.5)
    add(iso.boat(FRAME), 10.2, 7.6)

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
    sc.save(os.path.join(out, "iso_landscape.png"))
    sc.resize((sc.size[0] * 2, sc.size[1] * 2), Image.NEAREST).save(os.path.join(out, "iso_landscape_2x.png"))
    print("wrote iso_landscape.png", sc.size)
