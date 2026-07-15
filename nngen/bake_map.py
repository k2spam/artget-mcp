"""Бейк ассетов карты: procgen-геометрия + hqiso-LoRA стиль → игровые спрайты.

Три шага (см. RUNBOOK §8):
  prepare  — рендерит procgen-ассеты как блокауты + альфа-маски (любая машина)
  generate — img2img каждого блокаута через SDXL+LoRA (GPU-машина)
  finish   — вырезка по маске, квантизация в палитру, атласы + манифест (любая)

    python nngen/bake_map.py prepare
    python nngen/bake_map.py generate            # на 3080 Ti
    python nngen/bake_map.py finish

Выход: nngen/bake/out/<class>/<name>.png + manifest.json (якоря, футпринты).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BAKE = ROOT / "nngen" / "bake"
BLOCK = BAKE / "blockout"     # вход для GPU: <name>.png (RGB, нейтральный фон)
MASK = BAKE / "mask"          # альфа procgen-оригинала
RAW = BAKE / "raw"            # выход GPU: <name>.png
OUT = BAKE / "out"            # финальные спрайты
META = BAKE / "meta.json"     # якоря/футпринты/промпты

BG = (100, 116, 44)           # нейтральная "трава" под вырезку
GEN = 768                     # рабочее разрешение нейронки на ассет

BASE_PROMPT = ("hqiso, isometric pixel art, cozy fantasy village asset, "
               "warm olive palette, dark outlines, dense charming details, "
               "plain grass background")
NEG = ("blurry, photo, 3d render, text, watermark, frame, border, "
       "extra objects, cropped")


# ---- реестр ассетов карты ---------------------------------------------------

def registry():
    """name -> (render_fn, prompt-доп, strength). Вызывается лениво, чтобы
    generate-шаг на GPU не требовал повторного рендера."""
    from artgen import iso
    R = {}

    def houses():
        combos = [(w, r, st) for w in iso.WALL_MATERIALS
                  for r in ("thatch", "green", "red", "slate")
                  for st in (1, 2)]
        for i, (w, r, st) in enumerate(combos):
            name = f"house_{w}_{r}_{st}"
            R[name] = (lambda w=w, r=r, st=st, i=i:
                       iso.house(w, r, fx=2.0, fy=2.0, storeys=st, seed=i,
                                 smoke=False),
                       f"single cottage, {w} walls, {r} roof, detailed rooftop",
                       0.55)

    def trees():
        for sp in iso.TREE_SPECIES:
            for s in range(3):
                R[f"tree_{sp}_{s}"] = (
                    lambda sp=sp, s=s: iso.tree(sp, s),
                    f"single lush {sp} tree, layered clumpy canopy", 0.6)
        for sp in iso.CONIFER_SPECIES:
            for s in range(2):
                R[f"conifer_{sp}_{s}"] = (
                    lambda sp=sp, s=s: iso.conifer(sp, s),
                    "single pine tree, layered branches", 0.55)

    def props():
        items = {
            "well": lambda: iso.well_iso(),
            "barrel": lambda: iso.barrel(),
            "crate": lambda: iso.crate(),
            "firewood": lambda: iso.firewood(1),
            "garden_bed": lambda: iso.garden_bed(1),
            "lamp_post": lambda: iso.lamp_post(),
            "bench": lambda: iso.bench(),
            "bush": lambda: iso.bush(2),
            "rock": lambda: iso.rock(3),
            "flowers": lambda: iso.flowers(4),
            "stump": lambda: iso.stump(5),
            "boat": lambda: iso.boat(0),
        }
        for n, fn in items.items():
            R[f"prop_{n}"] = (fn, f"single {n.replace('_', ' ')} prop", 0.5)

    def terrain():
        # патч 3x3 тайла -> нейронка texturing -> вырежем центральный ромб
        def patch(kind, seed):
            def render():
                W, H = iso.HW * 7, iso.HH * 8 + 40
                im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                for j in range(3):
                    for i in range(3):
                        sx, sy = iso.project(i, j, 0)
                        im.alpha_composite(
                            iso.diamond(kind, seed=seed + i + j * 3,
                                        world=(i, j)),
                            (int(W // 2 + sx - iso.HW), int(20 + sy)))
                return im, W // 2, 20 + 2 * iso.HH  # якорь = центр. тайл
            return render
        for kind in ("grass", "meadow", "forest_floor", "path", "sand"):
            for s in range(4):
                R[f"tile_{kind}_{s}"] = (
                    patch(kind, s * 11),
                    f"seamless {kind.replace('_', ' ')} ground texture, "
                    "top-down isometric tiles", 0.4)

    houses(); trees(); props(); terrain()
    return R


# ---- шаги -------------------------------------------------------------------

def prepare():
    from artgen import iso  # noqa: F401 — проверка импорта
    for d in (BLOCK, MASK):
        d.mkdir(parents=True, exist_ok=True)
    meta = {}
    for name, (fn, prompt, strength) in registry().items():
        sp = fn()
        im, ax, ay = sp if isinstance(sp, tuple) else (sp, 0, 0)
        # блокаут: спрайт на нейтральном фоне, вписан в квадрат GEN
        pad = 40
        sq = max(im.width, im.height) + pad * 2
        canvas = Image.new("RGBA", (sq, sq), BG + (255,))
        ox, oy = (sq - im.width) // 2, (sq - im.height) // 2
        canvas.alpha_composite(im, (ox, oy))
        scale = GEN / sq
        canvas.convert("RGB").resize((GEN, GEN), Image.LANCZOS) \
              .filter(ImageFilter.GaussianBlur(0.8)).save(BLOCK / f"{name}.png")
        # маска-альфа в тех же координатах
        mask = Image.new("L", (sq, sq), 0)
        mask.paste(im.getchannel("A"), (ox, oy))
        mask.resize((GEN, GEN), Image.LANCZOS).save(MASK / f"{name}.png")
        meta[name] = {"prompt": prompt, "strength": strength,
                      "anchor": [(ox + ax) * scale, (oy + ay) * scale],
                      "native": sq}
    META.write_text(json.dumps(meta, indent=1))
    print(f"prepare: {len(meta)} блокаутов -> {BLOCK}")


def generate(steps=30, cfg=6.5):
    import torch
    from diffusers import AutoPipelineForImage2Image
    meta = json.loads(META.read_text())
    RAW.mkdir(parents=True, exist_ok=True)
    pipe = AutoPipelineForImage2Image.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16, variant="fp16")
    lora = ROOT / "nngen" / "models" / "hqiso_lora.safetensors"
    pipe.load_lora_weights(str(lora))
    pipe.enable_model_cpu_offload()
    todo = [n for n in meta if not (RAW / f"{n}.png").exists()]
    print(f"generate: {len(todo)} ассетов")
    for k, name in enumerate(todo):
        m = meta[name]
        src = Image.open(BLOCK / f"{name}.png").convert("RGB")
        g = torch.Generator("cpu").manual_seed(hash(name) % 2**32)
        img = pipe(prompt=f"{BASE_PROMPT}, {m['prompt']}",
                   negative_prompt=NEG, image=src, strength=m["strength"],
                   num_inference_steps=steps, guidance_scale=cfg,
                   generator=g).images[0]
        img.save(RAW / f"{name}.png")
        print(f"[{k + 1}/{len(todo)}] {name}")


def finish(export_scale=0.5):
    """Вырезка по маске + квантизация + даунскейл до игрового размера."""
    from artgen.palette import quantize
    meta = json.loads(META.read_text())
    manifest = {}
    for name, m in meta.items():
        raw_p = RAW / f"{name}.png"
        if not raw_p.exists():
            continue
        cls = name.split("_")[0]
        d = OUT / cls
        d.mkdir(parents=True, exist_ok=True)
        raw = Image.open(raw_p).convert("RGBA")
        mask = Image.open(MASK / f"{name}.png").convert("L")
        # лёгкое расширение маски — нейронка чуть выходит за силуэт
        mask = mask.filter(ImageFilter.MaxFilter(5))
        raw.putalpha(mask)
        # назад к нативному размеру procgen (GEN -> native), потом в игру
        native = m["native"]
        im = raw.resize((native, native), Image.LANCZOS)
        im = quantize(im)
        game = im.resize((int(native * export_scale),) * 2, Image.BOX)
        game = quantize(game)
        bbox = game.getbbox()
        game = game.crop(bbox)
        game.save(d / f"{name}.png")
        ax, ay = m["anchor"]
        manifest[name] = {
            "file": f"{cls}/{name}.png",
            "anchor": [ax / GEN * native * export_scale - bbox[0],
                       ay / GEN * native * export_scale - bbox[1]],
        }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"finish: {len(manifest)} спрайтов -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", "generate", "finish"])
    ap.add_argument("--steps", type=int, default=30)
    a = ap.parse_args()
    {"prepare": prepare, "finish": finish,
     "generate": lambda: generate(a.steps)}[a.step]()
