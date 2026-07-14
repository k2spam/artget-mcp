#!/usr/bin/env python3
"""pixelize — normalize ANY art to Heroquarium style: downscale to tile size +
snap to the game palette + clean binary alpha. Bridge for external art
(PixelLab / Retro Diffusion / Kenney / SDXL output / any image).

Examples:
  # single sprite -> 16x16 in the game palette
  python -m artgen.pixelize in.png -o out/tree.png

  # 4x4 atlas of large tiles -> 16 separate 16x16 into out/
  python -m artgen.pixelize sheet.png --grid 4 4 -o out/

  # atlas with 32px source tiles -> slice and shrink to 16
  python -m artgen.pixelize sheet.png --src-tile 32 -o out/

  # rebuild palette from a folder of reference assets
  python -m artgen.pixelize --rebuild-palette --assets references/tiles
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from PIL import Image

from .palette import PALETTE_JSON, colors as _palette_colors, quantize as _quantize

# Palette functions live in artgen.palette (single source of truth). These thin
# wrappers preserve the historical pixelize API used by the MCP layer.


def load_palette(path: str = PALETTE_JSON):
    data = json.load(open(path, encoding="utf-8"))
    colors = [_hex(c) for c in data["colors"]]
    return colors, int(data.get("tile", 16))


def _hex(h: str):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rebuild_palette(assets: str, path: str = PALETTE_JSON, tile: int = 16, min_count: int = 3):
    """Rebuild the palette from opaque pixels of all PNGs in `assets`."""
    from collections import Counter

    cnt: Counter = Counter()
    for f in sorted(glob.glob(os.path.join(assets, "*.png"))):
        im = Image.open(f).convert("RGBA")
        for px in im.getdata():
            if px[3] >= 128:
                cnt[px[:3]] += 1
    colors = ["#%02x%02x%02x" % c for c, n in cnt.most_common() if n >= min_count]
    json.dump({"tile": tile, "colors": colors}, open(path, "w"), indent=2)
    print(f"palette: {len(colors)} colours -> {path}")
    return colors


def quantize(im: Image.Image, palette=None, alpha_cut: int = 128, cache=None) -> Image.Image:
    """Snap an RGBA image to the palette; binary alpha. Delegates to artgen.palette."""
    return _quantize(im, palette, alpha_cut, cache)


def downscale(im: Image.Image, size: int, method: str) -> Image.Image:
    if im.size == (size, size):
        return im
    resample = {
        "nearest": Image.NEAREST,
        "box": Image.BOX,
        "lanczos": Image.LANCZOS,
        "bilinear": Image.BILINEAR,
    }[method]
    return im.resize((size, size), resample)


def slice_tiles(im: Image.Image, grid=None, src_tile=None):
    """Split an atlas into tiles. grid=(cols,rows) OR src_tile=px."""
    w, h = im.size
    if src_tile:
        cols, rows = w // src_tile, h // src_tile
        tw = th = src_tile
    elif grid:
        cols, rows = grid
        tw, th = w // cols, h // rows
    else:
        return [im]
    tiles = []
    for j in range(rows):
        for i in range(cols):
            tiles.append(im.crop((i * tw, j * th, i * tw + tw, j * th + th)))
    return tiles


def process(inp, out, palette, tile, method, grid, src_tile, alpha_cut):
    im = Image.open(inp).convert("RGBA")
    tiles = slice_tiles(im, grid, src_tile)
    cache: dict = {}
    made = []
    if len(tiles) == 1:
        res = quantize(downscale(tiles[0], tile, method), palette, alpha_cut, cache)
        dst = os.path.join(out, os.path.basename(inp)) if out.endswith("/") or os.path.isdir(out) else out
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        res.save(dst)
        made.append(dst)
    else:
        os.makedirs(out, exist_ok=True)
        base = os.path.splitext(os.path.basename(inp))[0]
        for k, t in enumerate(tiles):
            res = quantize(downscale(t, tile, method), palette, alpha_cut, cache)
            dst = os.path.join(out, f"{base}_{k:02d}.png")
            res.save(dst)
            made.append(dst)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description="Normalize art to the Heroquarium palette/size.")
    ap.add_argument("input", nargs="?", help="image or atlas (png/jpg)")
    ap.add_argument("-o", "--out", default="out/", help="file (single tile) or dir/ (many)")
    ap.add_argument("--tile", type=int, default=None, help="output tile size (default: from palette)")
    ap.add_argument("--method", default="box",
                    choices=["nearest", "box", "lanczos", "bilinear"],
                    help="downscale: box/lanczos for 'fat' art, nearest for already-pixel art")
    ap.add_argument("--grid", type=int, nargs=2, metavar=("COLS", "ROWS"),
                    help="slice atlas into COLS x ROWS")
    ap.add_argument("--src-tile", type=int, help="slice atlas into N-px source tiles")
    ap.add_argument("--alpha-cut", type=int, default=128, help="opacity threshold (0-255)")
    ap.add_argument("--palette", default=PALETTE_JSON, help="palette JSON")
    ap.add_argument("--rebuild-palette", action="store_true", help="rebuild palette from --assets and exit")
    ap.add_argument("--assets", help="folder of PNGs for --rebuild-palette")
    args = ap.parse_args(argv)

    if args.rebuild_palette:
        if not args.assets:
            ap.error("--rebuild-palette needs --assets DIR")
        rebuild_palette(assets=args.assets, path=args.palette)
        return 0

    if not args.input:
        ap.error("input required (or --rebuild-palette)")

    palette, ptile = load_palette(args.palette)
    tile = args.tile or ptile
    made = process(args.input, args.out, palette, tile, args.method,
                   tuple(args.grid) if args.grid else None, args.src_tile, args.alpha_cut)
    print(f"done: {len(made)} file(s), palette {len(palette)} colours, tile {tile}px")
    for m in made:
        print(" ", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
