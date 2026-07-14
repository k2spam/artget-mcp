#!/usr/bin/env python3
"""Isometric feel prototype: a small plot with grass + flagstone path + a
detailed house + props, depth-sorted. Run: python scripts/iso_prototype.py
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402

OX, OY = 600, 140          # screen origin
GW, GH = 12, 10            # ground grid


def is_path(i, j):
    return (i in (4, 5)) or (j in (4,)) or (j == 7 and i >= 5)


def build():
    scene = Image.new("RGBA", (1180, 800), (0, 0, 0, 0))

    # ground diamonds; path tiles get a grass fringe on edges bordering grass
    edge_nb = {"SE": (1, 0), "NW": (-1, 0), "SW": (0, 1), "NE": (0, -1)}
    for j in range(GH):
        for i in range(GW):
            if is_path(i, j):
                fringe = {e for e, (di, dj) in edge_nb.items() if not is_path(i + di, j + dj)}
                dia = iso.diamond("#cbb08a", seed=i * 13 + j * 7, kind="path", fringe=fringe)
            else:
                dia = iso.diamond("#4f7a3a", seed=i * 13 + j * 7, kind="grass")
            sx, sy = iso.project(i, j, 0)
            scene.alpha_composite(dia, (int(OX + sx - iso.HW), int(OY + sy)))

    objs = []

    def add(sprite_tuple, wx, wy, foot=(0, 0)):
        im, ax, ay = sprite_tuple
        objs.append(((wx + foot[0]) + (wy + foot[1]), im, ax, ay, wx, wy))

    # houses (varied): cottage, wide barn, tall 2-storey, small
    add(iso.house("timber", "red", fx=2.0, fy=2.2, seed=1), 1.0, 0.6, foot=(2.0, 2.2))
    add(iso.house("log", "wood", fx=2.8, fy=1.8, wh=1.2, seed=2), 6.4, 0.8, foot=(2.8, 1.8))
    add(iso.house("plaster", "slate", fx=1.8, fy=1.8, wh=2.4, rh=1.0, seed=3), 0.8, 6.0, foot=(1.8, 1.8))
    add(iso.house("stone", "thatch", fx=1.6, fy=1.6, seed=4), 8.4, 5.6, foot=(1.6, 1.6))

    # decor clusters
    add(iso.well_iso(), 6.2, 5.2, foot=(1, 1))
    add(iso.tree(), 10.6, 0.6); add(iso.tree(), 0.4, 9.2); add(iso.tree(), 10.8, 8.6)
    add(iso.bush(), 3.2, 0.5); add(iso.bush(), 0.6, 3.2); add(iso.bush(), 9.0, 4.6)
    add(iso.barrel(), 3.4, 2.6); add(iso.crate(), 9.5, 1.0); add(iso.crate(), 9.9, 1.4)
    add(iso.bench(), 2.4, 5.0); add(iso.mailbox(), 3.6, 3.6)
    for (fx_, fy_) in [(2.0, 2.9), (3.0, 2.9), (2.0, 3.9)]:
        add(iso.fence(), fx_, fy_)
    add(iso.lamp_post(), 3.6, 3.4); add(iso.lamp_post(), 6.0, 3.4)
    add(iso.lamp_post(), 3.6, 6.4); add(iso.bush(), 8.2, 6.2)

    for depth, im, ax, ay, wx, wy in sorted(objs, key=lambda t: t[0]):
        sx, sy = iso.project(wx, wy, 0)
        scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    # crop to content with a margin
    bbox = scene.getbbox()
    if bbox:
        m = 16
        scene = scene.crop((max(0, bbox[0] - m), max(0, bbox[1] - m),
                            min(scene.size[0], bbox[2] + m), min(scene.size[1], bbox[3] + m)))
    return scene


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    sc = build()
    bg = Image.new("RGBA", sc.size, (58, 58, 68, 255))
    bg.alpha_composite(sc)
    bg.save(os.path.join(out, "iso_proto.png"))
    bg.resize((bg.size[0] * 2, bg.size[1] * 2), Image.NEAREST).save(os.path.join(out, "iso_proto_2x.png"))
    sc = bg
    print("wrote iso_proto.png", sc.size)
