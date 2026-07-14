"""CLI for procedural generation.

Examples:
  python -m artgen.procgen terrain --tile 32 --seed 42 --variety 3 -o out/terrain/
  python -m artgen.procgen nature  --tile 32 --seed 42 -o out/nature/
  python -m artgen.procgen all -o out/
"""
from __future__ import annotations

import argparse
import os

from .. import TILE
from ..preview import contact_sheet
from . import nature, terrain


def _save(im, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, name + ".png")
    im.save(p)
    return p


def cmd_terrain(args):
    out = args.out
    made, tiles = [], []
    data = terrain.generate(tile=args.tile, seed=args.seed, variety=args.variety)
    for kind, variants in data.items():
        for i, im in enumerate(variants):
            made.append(_save(im, out, f"{kind}{i}"))
            tiles.append(im)
    if args.sheet:
        contact_sheet(tiles, cols=args.variety or 3).save(os.path.join(out, "_terrain_sheet.png"))
    return made


def cmd_nature(args):
    out = args.out
    made, tiles = [], []
    data = nature.generate(tile=args.tile, seed=args.seed, count=args.count)
    for kind, items in data.items():
        for i, im in enumerate(items):
            suffix = "" if len(items) == 1 else str(i)
            made.append(_save(im, out, f"{kind}{suffix}"))
            tiles.append(im)
    if args.sheet:
        contact_sheet(tiles, cols=6).save(os.path.join(out, "_nature_sheet.png"))
    return made


def cmd_all(args):
    args.out = os.path.join(args.out, "terrain")
    t = cmd_terrain(args)
    args.out = os.path.join(os.path.dirname(args.out), "nature")
    n = cmd_nature(args)
    return t + n


def main(argv=None):
    ap = argparse.ArgumentParser(prog="artgen.procgen", description="Procedural pixel-art generator.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--tile", type=int, default=TILE)
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("-o", "--out", default="out/")
        p.add_argument("--no-sheet", dest="sheet", action="store_false", help="skip contact sheet")

    pt = sub.add_parser("terrain"); common(pt); pt.add_argument("--variety", type=int, default=3)
    pn = sub.add_parser("nature");  common(pn); pn.add_argument("--count", type=int, default=1)
    pa = sub.add_parser("all");     common(pa)
    pa.add_argument("--variety", type=int, default=3)
    pa.add_argument("--count", type=int, default=1)

    args = ap.parse_args(argv)
    fn = {"terrain": cmd_terrain, "nature": cmd_nature, "all": cmd_all}[args.cmd]
    made = fn(args)
    print(f"done: {len(made)} file(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
