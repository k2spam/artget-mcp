"""Блокаут для img2img: превращает procgen-рендер в заготовку для SDXL.

v1: берёт готовый iso-рендер (например out/iso_world_1_5x.png или любой
рендер artgen/iso.py), приводит к квадрату 1024, слегка размывает пиксельную
решётку — SDXL лучше «дорисовывает» по мягкой подложке, чем по жёсткой сетке.

    python nngen/blockout.py out/iso_world_1_5x.png --out out/blockout.png

v2 (TODO): семантический рендер напрямую из artgen.iso — плоские заливки
по классам (крыша/стена/трава/дорога/вода) + карта для ControlNet-seg.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def build(src: Path, out: Path, size: int = 1024, blur: float = 1.2,
          bg: str = "#7a8a3a") -> None:
    im = Image.open(src).convert("RGBA")
    im = ImageOps.pad(im, (size, size), Image.LANCZOS,
                      color=(0, 0, 0, 0), centering=(0.5, 0.5))
    base = Image.new("RGBA", (size, size),
                     tuple(int(bg[i:i+2], 16) for i in (1, 3, 5)) + (255,))
    base.alpha_composite(im)
    rgb = base.convert("RGB")
    if blur > 0:
        rgb = rgb.filter(ImageFilter.GaussianBlur(blur))
    rgb.save(out)
    print(f"blockout: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out/blockout.png"))
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--blur", type=float, default=1.2)
    args = ap.parse_args()
    build(args.src, args.out, args.size, args.blur)
