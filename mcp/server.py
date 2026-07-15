#!/usr/bin/env python3
"""Heroquarium ArtGen — MCP server (isometric + actors + animations).

Exposes the iso generators as callable tools (stdio transport). Every tool
writes PNG(s) under `out/` and returns their paths plus a base64 PNG preview so
the assistant can show the result inline.

Run standalone:  python mcp/server.py
Register:        see mcp/README.md
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from artgen import iso, palette  # noqa: E402
from artgen import iso_actors as actors  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "mcp")
os.makedirs(OUT, exist_ok=True)


# ---- helpers --------------------------------------------------------------

def _save(im: Image.Image, name: str) -> str:
    path = os.path.join(OUT, name + ".png")
    im.save(path)
    return path


def _b64(im: Image.Image, scale: int = 3) -> str:
    if scale != 1:
        im = im.resize((im.size[0] * scale, im.size[1] * scale), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _result(im, name):
    return {"paths": [_save(im, name)], "preview_png_b64": _b64(im)}


# ---- plain generators (unit-testable; tools are thin wrappers) ------------

def gen_list_palette() -> dict:
    return {"tile": 16, "colors": palette.hex_colors(),
            "projection": {"HW": iso.HW, "HH": iso.HH, "ZS": iso.ZS}}


def gen_list_roster() -> dict:
    return {"actors": list(actors.ROSTER), "directions": list(actors.DIRS),
            "biomes": list(iso.BIOMES), "wall_materials": list(iso.WALL_MATERIALS),
            "roof_types": list(iso.ROOF_TYPES), "tree_species": list(iso.TREE_SPECIES),
            "conifer_species": list(iso.CONIFER_SPECIES)}


def gen_terrain(kind="grass", seed=0, world=(0, 0)) -> dict:
    return _result(iso.diamond(kind, seed=seed, world=tuple(world)), f"terrain_{kind}_{seed}")


def gen_water(frame=0, seed=0) -> dict:
    return _result(iso.water_tile(frame=frame, seed=seed), f"water_{seed}_{frame}")


def gen_coast(corners=(1, 0, 0, 0), seed=0, land_kind="grass") -> dict:
    im = iso.coast_tile(tuple(int(c) for c in corners), seed=seed, land_kind=land_kind)
    return _result(im, f"coast_{''.join(str(int(c)) for c in corners)}_{seed}")


def gen_house(walls="timber", roof="red", storeys=1, seed=0, smoke=True) -> dict:
    im, ax, ay = iso.house(walls=walls, roof=roof, storeys=storeys, seed=seed, smoke=smoke)
    r = _result(im, f"house_{walls}_{roof}_{storeys}_{seed}")
    r["anchor"] = [ax, ay]
    return r


def gen_prop(name="well", seed=0) -> dict:
    fn = {"fence": lambda: iso.fence(), "gate": lambda: iso.fence(gate=True),
          "well": iso.well_iso, "barrel": iso.barrel, "crate": iso.crate,
          "bench": iso.bench, "mailbox": iso.mailbox, "lamp_post": iso.lamp_post,
          "firewood": lambda: iso.firewood(seed), "garden_bed": lambda: iso.garden_bed(seed),
          "campfire": lambda: iso.campfire(0), "boat": lambda: iso.boat(0),
          "reeds": lambda: iso.reeds_patch(seed), "lily_pads": lambda: iso.lily_pads(seed),
          "bush": iso.bush, "rock": lambda: iso.rock(seed), "flowers": lambda: iso.flowers(seed),
          "stump": lambda: iso.stump(seed), "log": lambda: iso.log(seed)}
    if name not in fn:
        return {"error": f"unknown prop {name}", "choices": sorted(fn)}
    im, ax, ay = fn[name]()
    r = _result(im, f"prop_{name}_{seed}")
    r["anchor"] = [ax, ay]
    return r


def gen_tree(species="oak", seed=0, conifer=False) -> dict:
    im, ax, ay = (iso.conifer(species, seed) if conifer else iso.tree(species, seed))
    r = _result(im, f"tree_{species}_{seed}")
    r["anchor"] = [ax, ay]
    return r


def gen_actor(name="villager", direction="S", frame=0, seed=0) -> dict:
    im, ax, ay = actors.make(name, direction=direction, frame=frame, seed=seed)
    r = _result(im, f"actor_{name}_{direction}_{frame}_{seed}")
    r["anchor"] = [ax, ay]
    return r


def gen_actor_walk(name="villager", seed=0) -> dict:
    """Full 4-direction walk set (S/N/E/W), 4 frames each, as sprite sheets +
    an animation manifest. This is the movement set the game consumes."""
    adir = os.path.join(OUT, "walk", f"{name}_{seed}")
    os.makedirs(adir, exist_ok=True)
    paths, previews = [], {}
    for d in actors.DIRS:
        frames = [actors.make(name, d, f, seed=seed) for f in range(4)]
        sheet, fw, fh = iso.pack_sheet(frames)
        p = os.path.join(adir, f"{name}_{d}.png")
        sheet.save(p)
        paths.append(p)
        if d == "E":
            previews["E"] = _b64(sheet, scale=2)
    manifest = {"name": name, "dirs": list(actors.DIRS), "frames": 4, "fps": 8,
                "loop": True, "frame_w": fw, "frame_h": fh,
                "sheet_pattern": f"{name}_<DIR>.png",
                "note": "S=toward viewer, N=away, E=right, W=left"}
    mpath = os.path.join(adir, "manifest.json")
    json.dump(manifest, open(mpath, "w"), indent=2)
    paths.append(mpath)
    return {"paths": paths, "manifest": manifest, "preview_png_b64": previews.get("E")}


def gen_anim(effect="smoke", seed=0, nframes=8) -> dict:
    """Baked frame animation as a sprite sheet + manifest entry.
    effect in smoke/campfire/glow/water."""
    fn = {"smoke": lambda f: iso.smoke_plume(f, nframes, seed),
          "campfire": lambda f: iso.campfire(f, nframes, seed),
          "glow": lambda f: iso.glow(f, nframes, seed),
          "water": lambda f: (iso.water_tile(f, seed), 0, 0)}
    if effect not in fn:
        return {"error": f"unknown effect {effect}", "choices": sorted(fn)}
    frames = [fn[effect](f) for f in range(nframes)]
    sheet, fw, fh = iso.pack_sheet(frames)
    path = _save(sheet, f"anim_{effect}_{seed}")
    manifest = {"effect": effect, "frames": nframes, "frame_w": fw, "frame_h": fh,
                "fps": 8, "loop": True}
    return {"paths": [path], "manifest": manifest, "preview_png_b64": _b64(sheet, scale=2)}


# ---- nngen bridge (remote GPU worker over HTTP) ----------------------------

def _nn_endpoint() -> str | None:
    ep = os.environ.get("NNGEN_ENDPOINT")
    if ep:
        return ep.rstrip("/")
    cfg = os.path.join(ROOT, "nngen", "endpoint.txt")
    if os.path.exists(cfg):
        ep = open(cfg, encoding="utf-8").read().strip()
        if ep:
            return ep.rstrip("/")
    return None


def gen_nn(prompt="village", mode="txt2img", input_path="", strength=0.6,
           n=1, steps=30, seed=-1, size=1024) -> dict:
    """Neural hqiso generation via the GPU worker (nngen/worker.py).

    prompt = preset name (village/house/nature/villager/…) or free text.
    mode img2img needs input_path = procgen blockout PNG (repo-relative or abs).
    """
    import urllib.request

    ep = _nn_endpoint()
    if not ep:
        return {"error": "nngen worker endpoint not configured",
                "fix": "start nngen/worker.py on the GPU machine, then put "
                       "http://<gpu-ip>:8188 into nngen/endpoint.txt or "
                       "NNGEN_ENDPOINT env (see nngen/RUNBOOK.md §7)"}
    payload = {"prompt": prompt, "mode": mode, "strength": strength,
               "n": n, "steps": steps, "seed": seed, "size": size}
    if mode == "img2img":
        p = input_path if os.path.isabs(input_path) else os.path.join(ROOT, input_path)
        if not os.path.exists(p):
            return {"error": f"input image not found: {p}"}
        payload["image_b64"] = base64.b64encode(open(p, "rb").read()).decode("ascii")
    req = urllib.request.Request(
        ep + "/generate", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            res = json.loads(r.read())
    except Exception as e:
        return {"error": f"nngen worker unreachable at {ep}: {e}",
                "fix": "is nngen/worker.py running on the GPU machine? "
                       "firewall open for the port? see nngen/RUNBOOK.md §7"}
    out_dir = os.path.join(ROOT, "out", "nngen_remote")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for img in res.get("images", []):
        path = os.path.join(out_dir, img["name"])
        open(path, "wb").write(base64.b64decode(img["png_b64"]))
        paths.append(path)
    result = {"paths": paths, "seeds": res.get("seeds", []),
              "worker": res.get("device", "?")}
    if paths:
        prev = Image.open(paths[0])
        prev.thumbnail((512, 512))
        result["preview_png_b64"] = _b64(prev, scale=1)
    return result


# ---- MCP wiring (optional import; generators work without it) -------------

def _register(app):
    @app.tool()
    def list_palette() -> dict:
        "Palette colours + iso projection constants."
        return gen_list_palette()

    @app.tool()
    def list_roster() -> dict:
        "Available actors, directions, biomes, materials, tree species."
        return gen_list_roster()

    @app.tool()
    def iso_terrain(kind: str = "grass", seed: int = 0) -> dict:
        "Ground diamond for a biome (grass/meadow/forest_floor/sand/dirt/stone/snow/path)."
        return gen_terrain(kind, seed)

    @app.tool()
    def iso_water(frame: int = 0, seed: int = 0) -> dict:
        "Animated water diamond frame."
        return gen_water(frame, seed)

    @app.tool()
    def iso_coast(corners: list = [1, 0, 0, 0], seed: int = 0, land_kind: str = "grass") -> dict:
        "Organic shoreline diamond. corners=(top,right,bottom,left), 1=water."
        return gen_coast(corners, seed, land_kind)

    @app.tool()
    def iso_house(walls: str = "timber", roof: str = "red", storeys: int = 1,
                  seed: int = 0, smoke: bool = True) -> dict:
        "Iso house. walls log/timber/plaster/stone; roof red/slate/thatch/wood; storeys 1-2."
        return gen_house(walls, roof, storeys, seed, smoke)

    @app.tool()
    def iso_prop(name: str = "well", seed: int = 0) -> dict:
        "Iso decor/structure prop (well/fence/barrel/firewood/garden_bed/boat/…)."
        return gen_prop(name, seed)

    @app.tool()
    def iso_tree(species: str = "oak", seed: int = 0, conifer: bool = False) -> dict:
        "Iso tree. deciduous species oak/maple/birch/poplar/linden; conifer spruce/pine/fir."
        return gen_tree(species, seed, conifer)

    @app.tool()
    def iso_actor(name: str = "villager", direction: str = "S", frame: int = 0, seed: int = 0) -> dict:
        "One actor sprite (villager/trader/skeleton/goblin/animals/slime/…), dir S/N/E/W."
        return gen_actor(name, direction, frame, seed)

    @app.tool()
    def iso_actor_walk(name: str = "villager", seed: int = 0) -> dict:
        "Full 4-direction walk animation set (sheets + manifest) for an actor."
        return gen_actor_walk(name, seed)

    @app.tool()
    def iso_anim(effect: str = "smoke", seed: int = 0, nframes: int = 8) -> dict:
        "Baked effect animation sheet (smoke/campfire/glow/water) + manifest."
        return gen_anim(effect, seed, nframes)

    @app.tool()
    def nn_generate(prompt: str = "village", mode: str = "txt2img",
                    input_path: str = "", strength: float = 0.6, n: int = 1,
                    steps: int = 30, seed: int = -1) -> dict:
        ("Neural hqiso-style art via remote SDXL+LoRA GPU worker. prompt = "
         "preset (village/house/nature/villager) or free text; mode img2img "
         "beautifies a procgen blockout given via input_path. Slow (~1 min).")
        return gen_nn(prompt, mode, input_path, strength, n, steps, seed)


def _diagnostics() -> str:
    lines = [f"python={sys.version.split()[0]}", f"executable={sys.executable}",
             f"cwd={os.getcwd()}", f"plugin_root={ROOT}"]
    for mod in ("PIL", "numpy", "mcp"):
        try:
            __import__(mod)
            lines.append(f"dep {mod}: OK")
        except Exception as e:
            lines.append(f"dep {mod}: MISSING ({e})")
    return "\n".join(lines)


def main():
    # Always drop a startup log next to the server so connection failures are
    # diagnosable (Cowork shows no error when a stdio server dies on launch).
    diag = _diagnostics()
    try:
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "startup.log"), "w").write(diag + "\n")
    except Exception:
        pass
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as e:  # pragma: no cover
        sys.stderr.write(
            "heroquarium-artgen: cannot start — the 'mcp' package is missing.\n"
            "Install deps in the SAME python this server runs with:\n"
            "    pip install mcp pillow numpy\n"
            f"error: {e}\n{diag}\n")
        return 1
    try:
        import PIL  # noqa
        import numpy  # noqa
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"heroquarium-artgen: missing pillow/numpy: {e}\n{diag}\n")
        return 1
    app = FastMCP("heroquarium-artgen")
    _register(app)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
