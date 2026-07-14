#!/usr/bin/env python3
"""Compose a rich demo village: varied terrain + road network + detailed houses
+ decor + nature. Reproducible (seeded). Run: python scripts/demo_scene.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen.procgen import autotile as A          # noqa: E402
from artgen.procgen import buildings as B          # noqa: E402
from artgen.procgen import nature, terrain         # noqa: E402

T = 32
COLS, ROWS = 22, 15
SEED = 7


def build():
    rng = np.random.default_rng(SEED)
    W, H = COLS * T, ROWS * T
    scene = Image.new("RGBA", (W, H))

    # 1) one large continuous grass field (soft patches flow across the whole
    #    map -> no per-tile rhythm, like the reference)
    scene.alpha_composite(terrain.ground_rect("grass", W, H, SEED), (0, 0))

    # 2) road network (grass=1, path=0), overlaid via seamless autotile
    grid = np.ones((ROWS + 1, COLS + 1), int)
    hr = ROWS // 2
    grid[hr:hr + 2, :] = 0                 # main horizontal road
    grid[:, COLS // 2:COLS // 2 + 2] = 0    # vertical branch
    for r in range(ROWS):
        for c in range(COLS):
            idx = A.corner_index(grid[r, c], grid[r, c + 1], grid[r + 1, c + 1], grid[r + 1, c])
            if idx != 15:                   # 15 == all grass -> keep varied grass
                v = A._variant(r, c, SEED, 8)
                scene.alpha_composite(
                    A.transition("grass", "path", A.index_corners(idx), T, SEED, variant=v),
                    (c * T, r * T))

    road_rows = set(range(hr, hr + 2))
    road_cols = set(range(COLS // 2, COLS // 2 + 2))

    def px(cx, cy, im):
        scene.alpha_composite(im, (cx - im.size[0] // 2, cy - im.size[1]))

    def on_road(c, r):
        return r in road_rows or c in road_cols

    # 3) houses lining the road, each with decor
    houses = [
        (3, hr - 1, "M", "slate", "frame"),
        (7, hr - 1, "L", "red", "stone"),
        (13, hr - 1, "M", "thatch", "timber"),
        (17, hr + 3, "L", "slate", "stone"),
        (5, hr + 3, "S", "thatch", "timber"),
    ]
    for (c, r, sz, rf, wl) in houses:
        cx, cy = c * T + T // 2, r * T + T
        px(cx, cy, B.house(sz, rf, wl, SEED + c))
        # decor around the house
        px(cx - 22, cy, B.barrel(seed=c))
        px(cx + 22, cy, B.potted_plant(seed=c))
        px(cx - 30, cy + 8, B.woodpile(seed=c))
        px(cx + 30, cy + 6, B.lantern(seed=c))
        if sz != "S":
            px(cx + 14, cy + 10, B.bucket(seed=c))

    # a well + market stall + sign at the crossroads
    ccx = (COLS // 2) * T
    px(ccx - 40, hr * T + 2 * T + 20, B.well(seed=1))
    px(ccx + 60, hr * T - 6, B.market_stall(seed=2))
    px(ccx + 10, hr * T + 2 * T + 26, B.signpost(seed=3))

    # 4) nature scattered on grass, away from the road
    trees = [nature.tree_round, nature.tree_round, nature.tree_pine, nature.bush,
             nature.bush, nature.boulder, nature.flat_rock, nature.flowers,
             nature.grass_tuft, nature.mushroom_cluster, nature.fallen_branch]
    placed = 0
    tries = 0
    while placed < 34 and tries < 500:
        tries += 1
        c = int(rng.integers(0, COLS)); r = int(rng.integers(0, ROWS))
        if on_road(c, r) or on_road(c, r - 1):
            continue
        fn = trees[int(rng.integers(len(trees)))]
        px(c * T + T // 2, r * T + T, fn(T, SEED + tries))
        placed += 1

    return scene


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    sc = build()
    sc.save(os.path.join(out, "scene_v2.png"))
    sc.resize((sc.size[0] * 2, sc.size[1] * 2), Image.NEAREST).save(os.path.join(out, "scene_v2_2x.png"))
    print("wrote scene_v2.png", sc.size)
