#!/usr/bin/env python3
"""
pixelize — приводит ЛЮБОЙ арт к стилю Heroquarium: даунскейл до тайла + привязка
к палитре игры + чистая альфа. Мост «внешний сервис → наши ассеты».

Годится для выхода PixelLab / Retro Diffusion / Kenney / любой картинки.

Примеры:
  # один спрайт → 16×16 в палитре игры
  python tools/pixelize.py in.png -o ../src/assets/tree.png

  # атлас 4×4 больших тайлов → 16 отдельных 16×16 в папку out/
  python tools/pixelize.py sheet.png --grid 4 4 -o out/

  # атлас с тайлами по 32px исходника → нарезать и ужать до 16
  python tools/pixelize.py sheet.png --src-tile 32 -o out/

  # обновить палитру из текущих ассетов
  python tools/pixelize.py --rebuild-palette
"""
import argparse
import glob
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE_JSON = os.path.join(HERE, 'palette.json')
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'src', 'assets'))


def load_palette(path=PALETTE_JSON):
    data = json.load(open(path, encoding='utf-8'))
    colors = [_hex(c) for c in data['colors']]
    return colors, int(data.get('tile', 16))


def _hex(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rebuild_palette(assets=ASSETS, path=PALETTE_JSON, tile=16, min_count=3):
    """Пересобрать палитру из непрозрачных пикселей всех ассетов."""
    from collections import Counter
    cnt = Counter()
    for f in sorted(glob.glob(os.path.join(assets, '*.png'))):
        im = Image.open(f).convert('RGBA')
        for px in im.getdata():
            if px[3] >= 128:
                cnt[px[:3]] += 1
    colors = ['#%02x%02x%02x' % c for c, n in cnt.most_common() if n >= min_count]
    json.dump({'tile': tile, 'colors': colors}, open(path, 'w'), indent=2)
    print(f'палитра: {len(colors)} цветов -> {path}')
    return colors


def nearest(px, palette):
    """Ближайший цвет палитры. «Redmean» — дешёвое перцептивное расстояние."""
    r, g, b = px
    best, bd = palette[0], 1 << 30
    for (pr, pg, pb) in palette:
        rm = (r + pr) // 2
        dr, dg, db = r - pr, g - pg, b - pb
        d = (((512 + rm) * dr * dr) >> 8) + 4 * dg * dg + (((767 - rm) * db * db) >> 8)
        if d < bd:
            bd, best = d, (pr, pg, pb)
    return best


def quantize(im, palette, alpha_cut=128, cache=None):
    """RGBA-картинку точь-в-точь в палитру; альфа по порогу."""
    im = im.convert('RGBA')
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    src, dst = im.load(), out.load()
    cache = {} if cache is None else cache
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a < alpha_cut:
                continue
            key = (r, g, b)
            c = cache.get(key)
            if c is None:
                c = cache[key] = nearest(key, palette)
            dst[x, y] = (c[0], c[1], c[2], 255)
    return out


def downscale(im, size, method):
    if im.size == (size, size):
        return im
    resample = {
        'nearest': Image.NEAREST,
        'box': Image.BOX,
        'lanczos': Image.LANCZOS,
        'bilinear': Image.BILINEAR,
    }[method]
    return im.resize((size, size), resample)


def slice_tiles(im, grid=None, src_tile=None):
    """Разбить атлас на тайлы. grid=(cols,rows) ИЛИ src_tile=px."""
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
    im = Image.open(inp).convert('RGBA')
    tiles = slice_tiles(im, grid, src_tile)
    cache = {}
    made = []
    if len(tiles) == 1:
        res = quantize(downscale(tiles[0], tile, method), palette, alpha_cut, cache)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True) if not out.endswith('/') else None
        dst = os.path.join(out, os.path.basename(inp)) if out.endswith('/') or os.path.isdir(out) else out
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        res.save(dst)
        made.append(dst)
    else:
        os.makedirs(out, exist_ok=True)
        base = os.path.splitext(os.path.basename(inp))[0]
        for k, t in enumerate(tiles):
            res = quantize(downscale(t, tile, method), palette, alpha_cut, cache)
            dst = os.path.join(out, f'{base}_{k:02d}.png')
            res.save(dst)
            made.append(dst)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description='Привести арт к стилю/палитре Heroquarium.')
    ap.add_argument('input', nargs='?', help='картинка или атлас (png/jpg)')
    ap.add_argument('-o', '--out', default='out/', help='файл (один тайл) или папка/ (много)')
    ap.add_argument('--tile', type=int, default=None, help='размер тайла на выходе (по умолчанию из палитры)')
    ap.add_argument('--method', default='box',
                    choices=['nearest', 'box', 'lanczos', 'bilinear'],
                    help='даунскейл: box/lanczos для «жирного» арта, nearest для уже-пиксельного')
    ap.add_argument('--grid', type=int, nargs=2, metavar=('COLS', 'ROWS'),
                    help='нарезать атлас на COLS×ROWS')
    ap.add_argument('--src-tile', type=int, help='нарезать атлас на тайлы по N px исходника')
    ap.add_argument('--alpha-cut', type=int, default=128, help='порог непрозрачности (0-255)')
    ap.add_argument('--palette', default=PALETTE_JSON, help='JSON палитры')
    ap.add_argument('--rebuild-palette', action='store_true', help='пересобрать палитру из ассетов и выйти')
    args = ap.parse_args(argv)

    if args.rebuild_palette:
        rebuild_palette(path=args.palette)
        return 0

    if not args.input:
        ap.error('нужен input (или --rebuild-palette)')

    palette, ptile = load_palette(args.palette)
    tile = args.tile or ptile
    made = process(args.input, args.out, palette, tile, args.method,
                   tuple(args.grid) if args.grid else None, args.src_tile, args.alpha_cut)
    print(f'готово: {len(made)} файл(ов), палитра {len(palette)} цветов, тайл {tile}px')
    for m in made:
        print(' ', m)
    return 0


if __name__ == '__main__':
    sys.exit(main())
