"""Генерация hqiso-арта: SDXL + LoRA (diffusers). Требует GPU ~12 GB.

Режимы:
  txt2img — свободная генерация сцены/объекта по промпту
  img2img — «облагораживание» procgen-блокаута (см. blockout.py)

Примеры (из корня репо):
  python nngen/generate.py --prompt village --n 4
  python nngen/generate.py --mode img2img --input out/blockout.png \
      --prompt village --strength 0.6 --n 4
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LORA = ROOT / "nngen" / "models" / "hqiso_lora.safetensors"
MODEL = "stabilityai/stable-diffusion-xl-base-1.0"

TRIGGER = "hqiso, isometric pixel art"
PRESETS = {
    "village": (
        "cozy fantasy village, thatched and slate rooftops, stone-and-timber "
        "houses, winding dirt roads, river with wooden bridge, windmill, "
        "vegetable gardens, fences, lamp posts, lush trees and bushes, "
        "warm olive palette, dense charming details"
    ),
    "house": (
        "single cozy cottage, stone base, timber-frame walls, detailed "
        "thatched roof, flower beds, fence, warm olive palette, "
        "transparent-friendly plain grass background"
    ),
    "nature": (
        "nature props, leafy trees, pines, bushes, boulders, flowers, "
        "stumps, warm olive palette, plain grass background"
    ),
    "villager": (
        "single villager character, full body, simple pose, warm palette, "
        "plain background, game sprite"
    ),
}
NEGATIVE = (
    "blurry, photo, 3d render, text, watermark, logo, ui, frame, border, "
    "deformed, oversaturated"
)


def load_pipe(mode: str):
    from diffusers import (AutoPipelineForImage2Image,
                           AutoPipelineForText2Image)

    cls = AutoPipelineForText2Image if mode == "txt2img" else AutoPipelineForImage2Image
    pipe = cls.from_pretrained(MODEL, torch_dtype=torch.float16, variant="fp16")
    if LORA.exists():
        pipe.load_lora_weights(str(LORA))
        print(f"LoRA: {LORA.name}")
    else:
        print("!! LoRA не найдена — генерация базовой SDXL (стиль будет не тот)")
    pipe.enable_model_cpu_offload()  # укладываемся в 12 GB
    return pipe


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["txt2img", "img2img"], default="txt2img")
    ap.add_argument("--prompt", default="village",
                    help="имя пресета из PRESETS или свободный текст")
    ap.add_argument("--input", help="PNG-блокаут для img2img")
    ap.add_argument("--strength", type=float, default=0.6,
                    help="img2img: 0.4 держит структуру, 0.75 больше свободы")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cfg", type=float, default=6.5)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=-1)
    ap.add_argument("--out", default="out/nngen")
    args = ap.parse_args()

    prompt = f"{TRIGGER}, {PRESETS.get(args.prompt, args.prompt)}"
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    pipe = load_pipe(args.mode)

    stamp = datetime.now().strftime("%m%d_%H%M%S")
    for i in range(args.n):
        seed = args.seed if args.seed >= 0 else torch.seed() % 2**32
        g = torch.Generator("cpu").manual_seed(seed)
        kw = dict(prompt=prompt, negative_prompt=NEGATIVE,
                  num_inference_steps=args.steps, guidance_scale=args.cfg,
                  generator=g)
        if args.mode == "img2img":
            src = Image.open(ROOT / args.input).convert("RGB")
            src = src.resize((args.size, args.size), Image.LANCZOS)
            kw.update(image=src, strength=args.strength)
        else:
            kw.update(width=args.size, height=args.size)
        img = pipe(**kw).images[0]
        p = out_dir / f"{args.prompt[:16]}_{stamp}_{seed}.png"
        img.save(p)
        print(f"[{i+1}/{args.n}] {p}")


if __name__ == "__main__":
    main()
