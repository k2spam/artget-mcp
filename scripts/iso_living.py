#!/usr/bin/env python3
"""Iso living-world demo (Stage 4): a small scene animated over N frames —
chimney smoke, a campfire, water ripples, a flickering lamp — exported as a GIF
plus per-effect sprite sheets + an animation manifest (hybrid model: frames are
baked here; grass/tree sway is left to an engine shader).
Run: python scripts/iso_living.py
"""
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso  # noqa: E402

OX, OY = 300, 70
NF = 8            # frames per loop
FPS = 8


def _ground(scene):
    for j in range(7):
        for i in range(9):
            water = i >= 6 and j >= 4
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            if water:
                scene.alpha_composite(iso.water_tile(0, seed=i * 9 + j, foam=set()), pos)
            else:
                scene.alpha_composite(iso.diamond("grass", seed=i * 13 + j * 7, world=(i, j)), pos)


def frame_image(frame):
    scene = Image.new("RGBA", (760, 560), (0, 0, 0, 0))
    # ground (water animates)
    for j in range(7):
        for i in range(9):
            water = i >= 6 and j >= 4
            sx, sy = iso.project(i, j, 0)
            pos = (int(OX + sx - iso.HW), int(OY + sy))
            if water:
                scene.alpha_composite(iso.water_tile(frame, seed=i * 9 + j, foam=set()), pos)
            else:
                scene.alpha_composite(iso.diamond("grass", seed=i * 13 + j * 7, world=(i, j)), pos)

    def place(sprite, wx, wy):
        im, ax, ay = sprite
        sx, sy = iso.project(wx, wy, 0)
        scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    # house (2-storey), built without static smoke; animated smoke overlaid
    fx = fy = 2.0
    hx, hy = 1.0, 0.6
    place(iso.house("plaster", "red", fx=fx, fy=fy, storeys=2, seed=1, smoke=False), hx + 1, hy)
    # animated smoke at the chimney top
    wh, rh = 2.6, 1.1
    chx, chy = (hx + 1) + fx * 0.72 + 0.14, hy + fy * 0.3 + 0.14
    cz = wh + rh * 1.15
    im, ax, ay = iso.smoke_plume(frame, NF)
    sx, sy = iso.project(chx, chy, cz)
    scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    place(iso.tree("oak", 3), 4.4, 1.0)
    place(iso.campfire(frame, NF), 4.6, 4.4)
    place(iso.lamp_post(), 2.4, 4.2)
    # lamp flicker glow at the lamp head
    im, ax, ay = iso.glow(frame, NF)
    sx, sy = iso.project(2.4 + 0.15, 4.2, 2.25)
    scene.alpha_composite(im, (int(OX + sx - ax), int(OY + sy - ay)))

    bg = Image.new("RGBA", scene.size, (58, 58, 68, 255))
    bg.alpha_composite(scene)
    return bg.crop((120, 20, 700, 520))


def save_anim_assets(out):
    """Export per-effect sprite sheets + a manifest (for the engine)."""
    adir = os.path.join(out, "iso_anim")
    os.makedirs(adir, exist_ok=True)
    anims = {
        "smoke":    [iso.smoke_plume(f, NF) for f in range(NF)],
        "campfire": [iso.campfire(f, NF) for f in range(NF)],
        "glow":     [iso.glow(f, NF) for f in range(NF)],
        "water":    [(iso.water_tile(f), 0, 0) for f in range(NF)],
    }
    manifest = {}
    for name, frames in anims.items():
        sheet, fw, fh = iso.pack_sheet(frames)
        sheet.save(os.path.join(adir, f"{name}.png"))
        manifest[name] = {"sheet": f"{name}.png", "frames": NF, "frame_w": fw,
                          "frame_h": fh, "fps": FPS, "loop": True}
    manifest["_note"] = ("Baked frame animations. Grass/tree sway and subtle "
                         "water motion are expected to be added by an engine "
                         "vertex/UV shader (hybrid model).")
    with open(os.path.join(adir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return adir


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
    os.makedirs(out, exist_ok=True)
    frames = [frame_image(f) for f in range(NF)]
    ps = [im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=128) for im in frames]
    gif = os.path.join(out, "iso_living.gif")
    ps[0].save(gif, save_all=True, append_images=ps[1:], duration=int(1000 / FPS),
               loop=0, disposal=2)
    frames[0].resize((frames[0].size[0] * 2, frames[0].size[1] * 2), Image.NEAREST).save(
        os.path.join(out, "iso_living_frame0_2x.png"))
    adir = save_anim_assets(out)
    print("wrote", gif, "and anim sheets in", adir)
