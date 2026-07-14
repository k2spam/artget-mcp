"""MCP server generator functions: return contract + produce files."""
import importlib.util
import os

from PIL import Image

from artgen import palette

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("srv", os.path.join(_HERE, "mcp", "server.py"))
srv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srv)


def _check(r):
    assert "paths" in r and r["paths"], r
    assert "preview_png_b64" in r and len(r["preview_png_b64"]) > 50
    for p in r["paths"]:
        assert os.path.exists(p), p


def test_terrain_house_actor_contract_and_gamut():
    for r in (srv.gen_terrain("grass", 1), srv.gen_house("log", "red", 2, 1),
              srv.gen_actor("wolf", "E", 1, 1), srv.gen_tree("oak", 1),
              srv.gen_prop("well", 1), srv.gen_coast((1, 1, 0, 0), 1)):
        _check(r)
    png = srv.gen_actor("villager", "S", 0, 1)["paths"][0]
    assert palette.colors_outside(Image.open(png)) == set()


def test_actor_walk_full_set():
    r = srv.gen_actor_walk("deer", 2)
    assert r["manifest"]["dirs"] == ["S", "N", "E", "W"]
    assert r["manifest"]["frames"] == 4
    # 4 direction sheets + manifest.json
    assert sum(p.endswith(".png") for p in r["paths"]) == 4
    assert any(p.endswith("manifest.json") for p in r["paths"])


def test_anim_sheet():
    for eff in ("smoke", "campfire", "glow", "water"):
        r = srv.gen_anim(eff, 1)
        _check(r)
        assert r["manifest"]["effect"] == eff and r["manifest"]["loop"] is True


def test_list_roster_names_valid():
    rs = srv.gen_list_roster()
    assert "villager" in rs["actors"] and set(rs["directions"]) == {"S", "N", "E", "W"}
