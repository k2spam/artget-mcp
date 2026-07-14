#!/usr/bin/env python3
"""Iso actors demo (Stage 6): a walking GIF + per-actor walk sprite sheets and
an animation manifest. Run: python scripts/iso_actors_demo.py
"""
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402
from artgen import iso_actors as A  # noqa: E402

NF = 8
FPS = 8
# (name, seed, direction) — a mix of directions to show the full movement set
WALKERS = [("villager", 3, "E"), ("villager", 11, "S"), ("skeleton", 0, "N"),
           ("goblin", 1, "W"), ("wolf", 0, "E"), ("deer", 0, "S"),
           ("rabbit", 0, "N"), ("slime", 0, "S"), ("cow", 0, "E")]
DIR_VEC = {"S": (0.15, 0.15), "N": (-0.15, -0.15), "E": (0.22, -0.08), "W": (-0.22, 0.08)}


def walk_gif(out):
    OX, OY = 60, 30
    W, H = 560, 360
    frames = []
    for f in range(NF):
        scene = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for j in range(3):
            for i in range(10):
                sx, sy = iso.project(i, j, 0)
                scene.alpha_composite(iso.diamond("grass", seed=i * 7 + j * 5, world=(i, j)),
                                      (int(OX + sx - iso.HW), int(OY + sy)))
        objs = []
        for k, (name, seed, dr) in enumerate(WALKERS):
            dx, dy = DIR_VEC[dr]
            wx = 1.0 + (k % 5) * 1.7 + dx * (f - NF / 2)
            wy = 0.6 + (k // 5) * 1.6 + (k % 3) * 0.4 + dy * (f - NF / 2)
            im, ax, ay = A.make(name, dr, f, seed=seed)
            objs.append((wx + wy, im, ax, ay, wx, wy))
        for _, im, ax, ay, wx, wy in sorted(objs, key=lambda t: t[0]):
            sx, sy = iso.project(wx, wy, 0)
            scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))
        bg = Image.new("RGBA", (W, H), (58, 58, 68, 255))
        bg.alpha_composite(scene)
        frames.append(bg.crop((30, 10, 430, 300)))
    ps = [im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=128) for im in frames]
    gif = os.path.join(out, "iso_actors_walk.gif")
    ps[0].save(gif, save_all=True, append_images=ps[1:], duration=int(1000 / FPS),
               loop=0, disposal=2)
    return gif


def walk_sheets(out):
    adir = os.path.join(out, "iso_anim", "actors")
    os.makedirs(adir, exist_ok=True)
    manifest = {}
    for name in A.ROSTER:
        for dr in A.DIRS:                       # full movement set: S/N/E/W
            frames = [A.make(name, dr, f, seed=1) for f in range(4)]
            sheet, fw, fh = iso.pack_sheet(frames)
            sheet.save(os.path.join(adir, f"{name}_{dr}.png"))
        manifest[name] = {"dirs": list(A.DIRS), "frames": 4, "fps": FPS, "loop": True,
                          "sheet_pattern": f"{name}_<DIR>.png",
                          "note": "S=toward viewer, N=away, E=right, W=left; 4-frame walk"}
    with open(os.path.join(adir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return adir


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    g = walk_gif(out)
    a = walk_sheets(out)
    print("wrote", g, "and walk sheets in", a)
