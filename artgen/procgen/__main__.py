"""CLI for procedural generation.

Examples:
  python -m artgen.procgen terrain --tile 32 --seed 42 --variety 3 -o out/terrain/
  python -m artgen.procgen nature  --tile 32 --seed 42 -o out/nature/
  python -m artgen.procgen all -o out/
"""
from __future__ import annotations

import argparse
import json
import os

from .. import TILE
from ..preview import contact_sheet, gallery
from . import autotile, buildings, nature, roads, terrain


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


def cmd_autotile(args):
    out = args.out
    os.makedirs(out, exist_ok=True)
    tiles_dict = autotile.generate(args.from_kind, args.to_kind, tile=args.tile, seed=args.seed)
    made = []
    ordered = [tiles_dict[i] for i in range(16)]
    for idx, im in tiles_dict.items():
        made.append(_save(im, out, f"{args.from_kind}_{args.to_kind}_{idx:02d}"))
    if args.sheet:
        contact_sheet(ordered, cols=4).save(os.path.join(out, "_autotile_sheet.png"))
        autotile.render_map(args.from_kind, args.to_kind, 8, 8, args.tile, args.seed).save(
            os.path.join(out, "_autotile_map.png"))
    with open(os.path.join(out, f"{args.from_kind}_{args.to_kind}.manifest.json"), "w") as f:
        json.dump(autotile.manifest(args.from_kind, args.to_kind), f, indent=2)
    return made


def cmd_building(args):
    out = args.out
    im = buildings.house(args.size, args.roof, args.walls, args.seed)
    return [_save(im, out, f"house_{args.size}_{args.roof}_{args.walls}")]


def cmd_village(args):
    out = args.out
    cat = buildings.catalog(args.seed)
    made = [_save(im, out, name) for name, im in cat.items()]
    if args.sheet:
        gallery(list(cat.values()), cols=5).save(os.path.join(out, "_village_sheet.png"))
    return made


def cmd_road(args):
    out = args.out
    os.makedirs(out, exist_ok=True)
    im = roads.render(args.surface, args.cols, args.rows, args.tile, args.seed,
                      layout=args.layout, width=args.width)
    p = os.path.join(out, f"road_{args.surface}_{args.layout}.png")
    im.save(p)
    return [p]


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
    pe = sub.add_parser("autotile"); common(pe)
    pe.add_argument("--from", dest="from_kind", required=True, help="upper biome (e.g. grass)")
    pe.add_argument("--to", dest="to_kind", required=True, help="lower biome (e.g. dirt, water)")
    pb = sub.add_parser("building"); common(pb)
    pb.add_argument("--size", default="M", choices=list(buildings.SIZES))
    pb.add_argument("--roof", default="slate", choices=list(buildings.ROOFS))
    pb.add_argument("--walls", default="timber", choices=list(buildings.WALLS))
    pv = sub.add_parser("village"); common(pv)
    pr = sub.add_parser("road"); common(pr)
    pr.add_argument("--surface", default="path", help="path/cobble/gravel/sand/dirt")
    pr.add_argument("--layout", default="cross", choices=list(roads.LAYOUTS))
    pr.add_argument("--width", type=int, default=2)
    pr.add_argument("--cols", type=int, default=8)
    pr.add_argument("--rows", type=int, default=8)
    pa = sub.add_parser("all");     common(pa)
    pa.add_argument("--variety", type=int, default=3)
    pa.add_argument("--count", type=int, default=1)

    args = ap.parse_args(argv)
    fn = {"terrain": cmd_terrain, "nature": cmd_nature, "autotile": cmd_autotile,
          "building": cmd_building, "village": cmd_village, "road": cmd_road,
          "all": cmd_all}[args.cmd]
    made = fn(args)
    print(f"done: {len(made)} file(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
