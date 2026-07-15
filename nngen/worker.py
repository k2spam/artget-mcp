"""HTTP-воркер nngen для GPU-машины: держит SDXL+LoRA в памяти,
отдаёт генерации по сети MCP-серверу (tool nn_generate).

Запуск на машине с 3080 Ti (venv из RUNBOOK):
    python nngen/worker.py --host 0.0.0.0 --port 8188

Проверка:  curl http://localhost:8188/health
"""
from __future__ import annotations

import argparse
import base64
import io
from datetime import datetime
from pathlib import Path

import torch
from fastapi import FastAPI
from PIL import Image
from pydantic import BaseModel

from generate import LORA, MODEL, NEGATIVE, PRESETS, TRIGGER  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "nngen"
OUT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="hqiso nngen worker")
_pipes: dict = {}


def pipe(mode: str):
    if mode in _pipes:
        return _pipes[mode]
    from diffusers import (AutoPipelineForImage2Image,
                           AutoPipelineForText2Image)
    if mode == "txt2img":
        p = AutoPipelineForText2Image.from_pretrained(
            MODEL, torch_dtype=torch.float16, variant="fp16")
        if LORA.exists():
            p.load_lora_weights(str(LORA))
        p.enable_model_cpu_offload()
    else:  # img2img переиспользует веса txt2img
        p = AutoPipelineForImage2Image.from_pipe(pipe("txt2img"))
    _pipes[mode] = p
    return p


class Job(BaseModel):
    prompt: str = "village"
    mode: str = "txt2img"          # txt2img | img2img
    image_b64: str | None = None   # для img2img
    strength: float = 0.6
    n: int = 1
    steps: int = 30
    cfg: float = 6.5
    size: int = 1024
    seed: int = -1


@app.get("/health")
def health():
    return {"ok": True, "cuda": torch.cuda.is_available(),
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            "lora": LORA.exists()}


@app.post("/generate")
def generate(job: Job):
    prompt = f"{TRIGGER}, {PRESETS.get(job.prompt, job.prompt)}"
    p = pipe(job.mode)
    stamp = datetime.now().strftime("%m%d_%H%M%S")
    images, seeds = [], []
    for i in range(max(1, min(job.n, 8))):
        seed = job.seed if job.seed >= 0 else int(torch.seed() % 2**32)
        g = torch.Generator("cpu").manual_seed(seed)
        kw = dict(prompt=prompt, negative_prompt=NEGATIVE,
                  num_inference_steps=job.steps, guidance_scale=job.cfg,
                  generator=g)
        if job.mode == "img2img":
            src = Image.open(io.BytesIO(base64.b64decode(job.image_b64))).convert("RGB")
            kw.update(image=src.resize((job.size, job.size), Image.LANCZOS),
                      strength=job.strength)
        else:
            kw.update(width=job.size, height=job.size)
        img = p(**kw).images[0]
        name = f"{job.prompt[:16].replace(' ', '_')}_{stamp}_{seed}.png"
        img.save(OUT / name)  # локальная копия на GPU-машине
        buf = io.BytesIO()
        img.save(buf, "PNG")
        images.append({"name": name,
                       "png_b64": base64.b64encode(buf.getvalue()).decode()})
        seeds.append(seed)
    return {"images": images, "seeds": seeds,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}


if __name__ == "__main__":
    import uvicorn
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8188)
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
