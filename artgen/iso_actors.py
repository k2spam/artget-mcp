"""Iso actors: villagers/NPCs, animals and enemies with primitive walk cycles.

Parametric billboards (like the flora) built from a few generators:
- person()  : humanoid (villager/trader/skeleton/goblin), 4 iso directions
              (front/back + mirror), 4-frame walk, randomised palette + face.
- animal()  : side-view quadruped (rabbit/deer/wolf/fox/boar/bear/sheep/cow),
              2 directions (mirror), 4-frame walk.
- slime()   : bouncing blob. bird() : chicken / bat with flap.

Randomisation is seed-driven (clothing colours, faces). All palette-snapped,
outlined, top-left light. Directions: SE/SW = toward viewer (face shown),
NE/NW = away (back). Anchor = feet.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .iso import _billboard, _rgb, _shade  # noqa

SKIN = ["#e8b088", "#e8c8a8", "#d8a878", "#94684a"]
HAIR = ["#3a2417", "#5a3a24", "#6e4a2f", "#8f5a3a", "#e3d05a", "#565061", "#b55a33"]
SHIRT = ["#b0453a", "#3f75ad", "#4a8f4a", "#e3d05a", "#8f5a3a", "#7a7485", "#cc6452", "#4a5a8f", "#5f8f46"]
PANTS = ["#4a3a2a", "#3a2a1a", "#565061", "#5a3a24", "#4a5a8f", "#6e4a2f"]

# movement directions (screen): S=toward viewer, N=away, E=right, W=left
DIRS = ("S", "N", "E", "W")


def _pick(rng, lst):
    return lst[int(rng.integers(len(lst)))]


def person(kind="villager", direction="S", frame=0, seed=0):
    rng = np.random.default_rng(seed)
    skin, hair, shirt, pants = _pick(rng, SKIN), _pick(rng, HAIR), _pick(rng, SHIRT), _pick(rng, PANTS)
    hat, hatcol = rng.random() < 0.35, _pick(rng, SHIRT)
    ears = bone = False
    if kind == "skeleton":
        skin, shirt, pants, hair, hat, bone = "#e8e8e0", None, None, None, False, True
    elif kind == "goblin":
        skin, hair, hat, ears = _pick(rng, ["#5aa843", "#4a8f4a", "#5f8f46"]), None, False, True
        shirt = _pick(rng, ["#5a3a24", "#6e4a2f", "#7a5238"])
    elif kind == "trader":
        hat, shirt = True, _pick(rng, ["#b0453a", "#4a5a8f", "#8f4f2f"])

    W, H, cx = 22, 30, 11
    ph = frame % 4
    bob = [0, -1, 0, -1][ph]
    tc = _rgb(shirt) if shirt else _rgb("#c8c8c0")
    ac = tc if shirt else _rgb(skin)
    legc = _rgb(pants) if pants else _rgb("#e8e8e0")
    side = direction in ("E", "W")
    back = direction == "N"

    def head(d, hy, profile=False):
        d.ellipse([cx - 4, hy - 4, cx + 4, hy + 4], fill=_rgb(skin))
        if ears:
            d.polygon([(cx - 4, hy - 1), (cx - 8, hy - 3), (cx - 4, hy + 2)], fill=_rgb(skin))
            d.polygon([(cx + 4, hy - 1), (cx + 8, hy - 3), (cx + 4, hy + 2)], fill=_rgb(skin))
        if hair:
            if back:
                d.ellipse([cx - 4, hy - 4, cx + 4, hy + 3], fill=_rgb(hair))
            elif profile:
                d.chord([cx - 4, hy - 5, cx + 3, hy + 1], 150, 360, fill=_rgb(hair))
            else:
                d.chord([cx - 4, hy - 5, cx + 4, hy + 2], 180, 360, fill=_rgb(hair))
        if not back:
            eye = _rgb("#241d2b")
            if profile:
                d.point((cx + 2, hy), fill=eye)
                d.point((cx + 4, hy + 1), fill=_rgb(skin))  # nose bump
                if bone:
                    d.rectangle([cx + 1, hy - 1, cx + 3, hy + 1], fill=eye)
            elif bone:
                d.rectangle([cx - 3, hy - 1, cx - 1, hy + 1], fill=eye)
                d.rectangle([cx + 1, hy - 1, cx + 3, hy + 1], fill=eye)
            else:
                es = 1 + int(seed % 2)
                d.point((cx - es, hy), fill=eye)
                d.point((cx + es, hy), fill=eye)
        if hat:
            d.rectangle([cx - 5, hy - 4, cx + 5, hy - 3], fill=_rgb(hatcol))
            d.rectangle([cx - 3, hy - 7, cx + 3, hy - 4], fill=_rgb(hatcol))

    def draw(d):
        hy = 6 + bob
        if side:  # profile: scissoring legs + one swinging arm
            s = [3, 0, -3, 0][ph]
            d.line([(cx, 18 + bob), (cx + s, 26)], fill=legc, width=2)
            d.line([(cx, 18 + bob), (cx - s, 26)], fill=legc, width=2)
            d.rectangle([cx - 3, 10 + bob, cx + 3, 19 + bob], fill=tc)
            if bone:
                for ry in range(12, 19, 2):
                    d.line([(cx - 2, ry + bob), (cx + 2, ry + bob)], fill=_rgb("#a8a8a0"))
            a = [3, 0, -3, 0][ph]
            d.line([(cx + 1, 11 + bob), (cx + 1 + a, 17 + bob)], fill=ac, width=2)
            d.point((cx + 1 + a, 17 + bob), fill=_rgb(skin))
            head(d, hy, profile=True)
        else:  # front (S) / back (N)
            liftL, liftR = (2 if ph == 1 else 0), (2 if ph == 3 else 0)
            armL = [0, 2, 0, -2][ph]
            armR = -armL
            d.rectangle([cx - 3, 18 + bob, cx - 1, 26 - liftL], fill=legc)
            d.rectangle([cx + 1, 18 + bob, cx + 3, 26 - liftR], fill=legc)
            d.rectangle([cx - 4, 25 - liftL, cx - 1, 26 - liftL], fill=_rgb("#3a2417"))
            d.rectangle([cx + 1, 25 - liftR, cx + 4, 26 - liftR], fill=_rgb("#3a2417"))
            d.rectangle([cx - 4, 10 + bob, cx + 4, 19 + bob], fill=tc)
            if bone:
                for ry in range(12, 19, 2):
                    d.line([(cx - 3, ry + bob), (cx + 3, ry + bob)], fill=_rgb("#a8a8a0"))
                d.line([(cx, 10 + bob), (cx, 19 + bob)], fill=_rgb("#a8a8a0"))
            d.rectangle([cx - 6, 10 + bob, cx - 4, 17 + bob + armL], fill=ac)
            d.rectangle([cx + 4, 10 + bob, cx + 6, 17 + bob + armR], fill=ac)
            d.rectangle([cx - 6, 16 + bob + armL, cx - 4, 18 + bob + armL], fill=_rgb(skin))
            d.rectangle([cx + 4, 16 + bob + armR, cx + 6, 18 + bob + armR], fill=_rgb(skin))
            head(d, hy, profile=False)

    im, ax, ay = _billboard(draw, W, H, cx, 27, shadow_r=6)
    if direction == "W":
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        ax = W - ax
    return im, ax, ay


# ---- quadrupeds -----------------------------------------------------------

ANIMALS = {
    # body, scale, ears, tail, feature, extra
    "rabbit": ("#c8c8c0", 0.7, "long", "puff", None, {}),
    "deer":   ("#b0623a", 1.1, "short", "short", "antlers", {}),
    "wolf":   ("#7a7485", 1.0, "point", "bushy", "snout", {}),
    "fox":    ("#cc7444", 0.85, "point", "bushy_w", "snout", {}),
    "boar":   ("#5a3a24", 1.0, "small", "tiny", "tusks", {}),
    "bear":   ("#6e4a2f", 1.3, "round", "tiny", "snout", {}),
    "sheep":  ("#e8e4dc", 0.95, "small", "tiny", "wool", {"legdark": True}),
    "cow":    ("#e8e8e0", 1.2, "small", "tuft", "horns", {"spots": True}),
}


def animal(species="wolf", direction="E", frame=0, seed=0):
    body, scale, ears, tail, feature, extra = ANIMALS.get(species, ANIMALS["wolf"])
    W, H = 40, 32
    ground = H - 3
    ph = frame % 4
    bc, dark, light = _rgb(body), _shade(body, 0.8), _shade(body, 1.15)
    legc = _rgb("#3a2a1a") if extra.get("legdark") else dark
    eye = _rgb("#241d2b")

    def _ears_top(d, cx, top):
        if ears == "long":
            d.rectangle([cx - 4, top - 7, cx - 2, top], fill=bc)
            d.rectangle([cx + 2, top - 7, cx + 4, top], fill=bc)
        elif ears == "point":
            d.polygon([(cx - 4, top), (cx - 5, top - 6), (cx - 1, top - 1)], fill=bc)
            d.polygon([(cx + 4, top), (cx + 5, top - 6), (cx + 1, top - 1)], fill=bc)
        elif ears == "round":
            d.ellipse([cx - 5, top - 5, cx - 1, top - 1], fill=bc)
            d.ellipse([cx + 1, top - 5, cx + 5, top - 1], fill=bc)
        else:
            d.polygon([(cx - 3, top), (cx - 4, top - 4), (cx, top - 1)], fill=bc)
            d.polygon([(cx + 3, top), (cx + 4, top - 4), (cx, top - 1)], fill=bc)
        if feature == "antlers":
            for sx in (cx - 2, cx + 2):
                d.line([(sx, top - 1), (sx, top - 9)], fill=_rgb("#cbb08a"))
                d.line([(sx, top - 6), (sx + (2 if sx > cx else -2), top - 9)], fill=_rgb("#cbb08a"))
        if feature == "horns":
            d.line([(cx - 3, top), (cx - 6, top - 4)], fill=_rgb("#e8e4dc"))
            d.line([(cx + 3, top), (cx + 6, top - 4)], fill=_rgb("#e8e4dc"))

    def side(d):
        cx = 20
        bw, bh, legh = int(12 * scale), int(6 * scale), 6
        by = ground - legh - bh
        lx = [cx - bw + 3, cx - bw + 7, cx + bw - 8, cx + bw - 4]
        gait = [3, -3, -3, 3]
        for k, x in enumerate(lx):
            off = gait[k] if ph == 1 else (-gait[k] if ph == 3 else 0)
            d.line([(x, by + bh), (x + off, ground)], fill=(dark if k in (1, 2) else legc), width=2)
        d.ellipse([cx - bw, by - bh, cx + bw, by + bh], fill=bc)
        d.ellipse([cx - bw, by - bh, cx, by], fill=light)
        if extra.get("spots"):
            d.ellipse([cx - 6, by - 3, cx - 1, by + 2], fill=dark)
            d.ellipse([cx + 3, by - 1, cx + 8, by + 4], fill=dark)
        if feature == "wool":
            for ox in range(-bw, bw, 4):
                d.ellipse([cx + ox, by - bh - 2, cx + ox + 5, by - bh + 4], fill=light)
        tx = cx - bw
        if tail in ("bushy", "bushy_w"):
            d.ellipse([tx - 5, by - bh, tx + 2, by + 2], fill=bc)
            if tail == "bushy_w":
                d.ellipse([tx - 5, by - 2, tx - 1, by + 2], fill=_rgb("#e8e4dc"))
        elif tail == "puff":
            d.ellipse([tx - 4, by, tx, by + 4], fill=_rgb("#e8e8e0"))
        elif tail == "tuft":
            d.line([(tx, by - bh + 1), (tx - 4, by + 2)], fill=dark)
        else:
            d.line([(tx, by - 2), (tx - 3, by + 1)], fill=dark)
        hx, hyc = cx + bw - 1, by - 2
        d.ellipse([hx - 4, hyc - 4, hx + 6, hyc + 5], fill=bc)
        _ears_top(d, hx + 1, hyc - 3)
        if feature == "snout":
            d.ellipse([hx + 3, hyc + 1, hx + 9, hyc + 5], fill=bc)
            d.point((hx + 8, hyc + 3), fill=eye)
        if feature == "tusks":
            d.ellipse([hx + 3, hyc + 1, hx + 8, hyc + 6], fill=dark)
            d.point((hx + 8, hyc + 5), fill=_rgb("#e8e8e0"))
        d.point((hx + 2, hyc - 1), fill=eye)

    def frontback(d, is_front):
        cx = 20
        bw, bh, legh = int(6 * scale) + 2, int(7 * scale), 6
        by = ground - legh - bh
        liftL, liftR = (2 if ph == 1 else 0), (2 if ph == 3 else 0)
        d.rectangle([cx - 5, by + bh - 2, cx - 2, ground - liftL], fill=legc)
        d.rectangle([cx + 2, by + bh - 2, cx + 5, ground - liftR], fill=legc)
        d.ellipse([cx - bw, by, cx + bw, by + bh + 2], fill=bc)
        if extra.get("spots"):
            d.ellipse([cx - 4, by + 2, cx, by + 6], fill=dark)
        if feature == "wool":
            for oy in (by, by + 4):
                for ox in range(-bw, bw, 4):
                    d.ellipse([cx + ox, oy, cx + ox + 5, oy + 5], fill=light)
        hy = by - 3
        d.ellipse([cx - 5, hy - 5, cx + 5, hy + 5], fill=bc)
        _ears_top(d, cx, hy - 4)
        if is_front:
            d.point((cx - 2, hy - 1), fill=eye)
            d.point((cx + 2, hy - 1), fill=eye)
            if feature in ("snout", "tusks"):
                d.ellipse([cx - 2, hy + 1, cx + 2, hy + 5], fill=dark)
        else:  # back: tail up the centre
            if tail in ("bushy", "bushy_w"):
                d.ellipse([cx - 2, by - 4, cx + 3, by + 4], fill=bc)
            else:
                d.line([(cx, by), (cx, by - 5)], fill=dark)

    if direction in ("E", "W"):
        im, ax, ay = _billboard(side, W, H, 20, ground, shadow_r=int(11 * scale))
        if direction == "W":
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            ax = W - ax
        return im, ax, ay
    return _billboard(lambda d: frontback(d, direction == "S"), W, H, 20, ground, shadow_r=int(9 * scale))


def slime(frame=0, seed=0, color="#5aa843"):
    ph = frame % 4
    squash = [0, 3, 0, 1][ph]
    W, H = 24, 20

    def draw(d):
        cx, base = 12, 17
        w = 9 + squash
        h = 9 - squash
        d.ellipse([cx - w, base - h * 2, cx + w, base], fill=_rgb(color))
        d.ellipse([cx - w + 2, base - h * 2 + 1, cx + 1, base - h], fill=_shade(color, 1.2))
        for ex in (cx - 3, cx + 3):
            d.ellipse([ex - 1, base - h - 4, ex + 2, base - h], fill=_rgb("#241d2b"))
            d.point((ex, base - h - 3), fill=_rgb("#e8e8e0"))
    return _billboard(draw, W, H, 12, 18, shadow_r=9)


def bird(kind="chicken", frame=0, seed=0):
    ph = frame % 4
    W, H = 22, 22

    def draw(d):
        if kind == "bat":
            cx, cy = 11, 10
            wing = [6, 3, 6, 9][ph]
            d.polygon([(cx, cy), (cx - 10, cy - wing + 4), (cx - 4, cy + 2)], fill=_rgb("#3a3a44"))
            d.polygon([(cx, cy), (cx + 10, cy - wing + 4), (cx + 4, cy + 2)], fill=_rgb("#3a3a44"))
            d.ellipse([cx - 3, cy - 2, cx + 3, cy + 5], fill=_rgb("#241d2b"))
            d.point((cx - 1, cy), fill=_rgb("#b0453a"))
            d.point((cx + 1, cy), fill=_rgb("#b0453a"))
        else:  # chicken
            cx, base = 11, 18
            d.ellipse([cx - 5, base - 8, cx + 5, base], fill=_rgb("#e8e8e0"))
            d.ellipse([cx + 2, base - 12, cx + 8, base - 6], fill=_rgb("#e8e8e0"))  # head
            d.polygon([(cx + 8, base - 9), (cx + 11, base - 8), (cx + 8, base - 7)], fill=_rgb("#e3d05a"))
            d.line([(cx + 5, base - 11), (cx + 6, base - 14)], fill=_rgb("#b0453a"))  # comb
            d.point((cx + 6, base - 10), fill=_rgb("#241d2b"))
            lift = [0, 2, 0, 2][ph]
            d.line([(cx - 1, base), (cx - 1, base + 2 - lift)], fill=_rgb("#e3d05a"))
            d.line([(cx + 2, base), (cx + 2, base + 2 - (2 - lift))], fill=_rgb("#e3d05a"))
    return _billboard(draw, W, H, 11, H - 2, shadow_r=6)


# ---- roster ---------------------------------------------------------------

def make(name, direction="S", frame=0, seed=0):
    if name in ("villager", "trader", "skeleton", "goblin"):
        return person(name, direction, frame, seed)
    if name in ANIMALS:
        return animal(name, direction, frame, seed)
    if name == "slime":
        return slime(frame, seed)
    if name in ("chicken", "bat"):
        return bird(name, frame, seed)
    raise ValueError(f"unknown actor {name!r}")


ROSTER = (["villager", "trader", "skeleton", "goblin"] + list(ANIMALS)
          + ["slime", "chicken", "bat"])
