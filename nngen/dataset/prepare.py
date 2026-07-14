"""Подготовка датасета для обучения hqiso LoRA.

Читает nngen/dataset/sources.txt, режет референсы на кропы 1024x1024
(stride 512), отбрасывает малоинформативные (почти однотонные / прозрачные),
пишет пары PNG + .txt caption в nngen/dataset/train/hqiso/.

Запуск (из корня репо, GPU не нужен):
    python nngen/dataset/prepare.py [--size 1024] [--stride 512] [--min-std 18]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "train" / "hqiso"
SOURCES = Path(__file__).resolve().parent / "sources.txt"

BASE_CAPTION = (
    "hqiso, isometric pixel art, cozy fantasy village, warm olive palette, "
    "detailed rooftops, soft shading, dense props"
)


def read_sources() -> list[tuple[Path, str, int]]:
    items = []
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [s.strip() for s in line.split("|")]
        p = ROOT / parts[0]
        if not p.exists():
            print(f"!! пропуск (нет файла): {p}")
            continue
        tags = parts[1] if len(parts) > 1 else ""
        max_crops = int(parts[2]) if len(parts) > 2 and parts[2] else 999
        items.append((p, tags, max_crops))
    return items


def informative(arr: np.ndarray, min_std: float) -> bool:
    """Кроп полезен: не прозрачный, не однотонный, без крупных
    белых/чёрных зон (разделители листов, фон изо-ромбов, рамки)."""
    if arr.shape[2] == 4 and arr[..., 3].mean() < 128:
        return False
    rgb = arr[..., :3].astype(np.float32)
    if float(rgb.std(axis=(0, 1)).mean()) < min_std:
        return False
    white_px = (arr[..., :3] > 240).all(axis=-1)
    black_px = (arr[..., :3] < 15).all(axis=-1)
    if white_px.mean() > 0.08 or black_px.mean() > 0.10:
        return False
    # почти полностью белая строка = разделитель листов в кадре
    if (white_px.mean(axis=1) > 0.9).any():
        return False
    return True


def split_panels(im: Image.Image, min_h: int = 200) -> list[Image.Image]:
    """Режет склейку из нескольких панелей по горизонтальным белым полосам."""
    arr = np.asarray(im.convert("RGB"))
    white_rows = ((arr > 240).all(axis=-1).mean(axis=1) > 0.95)
    if not white_rows.any():
        return [im]
    panels, start = [], None
    for y, w in enumerate(list(white_rows) + [True]):
        if not w and start is None:
            start = y
        elif w and start is not None:
            if y - start >= min_h:
                panels.append(im.crop((0, start, im.width, y)))
            start = None
    return panels or [im]


def _grid(extent: int, size: int, stride: int) -> list[int]:
    xs = list(range(0, extent - size + 1, stride)) or [0]
    if xs[-1] != extent - size:
        xs.append(extent - size)
    return xs


def crops(im: Image.Image, size: int, stride: int):
    """Мультимасштабные окна: size, 0.75*size, 0.625*size (апскейл nearest).

    Источники в основном ~1024px, одиночный кроп 1024 даёт слишком мало
    сэмплов — меньшие окна добавляют разнообразия композиций.
    """
    w, h = im.size
    wins = [x for x in (size, int(size * 0.75), int(size * 0.625))
            if x <= min(w, h)]
    if not wins:
        # узкая панель: квадратные окна по меньшей стороне
        wins = [min(w, h)]
    seen = set()
    for win in wins:
        st = max(win // 2, stride * win // size)
        for y in _grid(h, win, st):
            for x in _grid(w, win, st):
                key = (x // 32, y // 32, win // 128)
                if key in seen:
                    continue
                seen.add(key)
                c = im.crop((x, y, x + win, y + win))
                if win != size:
                    c = c.resize((size, size), Image.NEAREST)
                yield c, f"w{win}_{x}_{y}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--stride", type=int, default=512)
    ap.add_argument("--min-std", type=float, default=18.0)
    args = ap.parse_args()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    total = 0
    for src, tags, max_crops in read_sources():
        im = Image.open(src).convert("RGBA")
        if "wm_br" in tags:  # срезать ватермарку в правом-нижнем углу
            tags = ", ".join(t for t in tags.split(", ") if t != "wm_br")
            w, h = im.size
            im = im.crop((0, 0, w, int(h * 0.90)))
        kept = 0
        for pi, panel in enumerate(split_panels(im)):
            for crop, key in crops(panel, args.size, args.stride):
                if kept >= max_crops:
                    break
                arr = np.asarray(crop)
                if not informative(arr, args.min_std):
                    continue
                name = f"{src.stem.replace(' ', '_')}_p{pi}_{key}"
                crop.convert("RGB").save(OUT / f"{name}.png")
                caption = BASE_CAPTION + (f", {tags}" if tags else "")
                (OUT / f"{name}.txt").write_text(caption, encoding="utf-8")
                kept += 1
        total += kept
        print(f"{src.name}: {kept} кропов")

    print(f"Итого: {total} сэмплов в {OUT}")
    if total < 30:
        print("!! Датасет тонкий (<30). Добавь референсов в references/iso/ "
              "(см. prompts.md, раздел «догенерация референсов»).")


if __name__ == "__main__":
    main()
