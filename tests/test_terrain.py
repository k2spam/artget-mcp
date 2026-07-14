"""M2 acceptance: terrain + nature are deterministic, in-gamut, and ground
tiles are seamless (edges continue when repeated)."""
import numpy as np

from artgen import palette
from artgen.procgen import nature, terrain


def _outside(im):
    return palette.colors_outside(im)


def test_all_biomes_in_gamut_and_sized():
    for kind in terrain.BIOMES:
        im = terrain.ground(kind, tile=32, seed=1)
        assert im.size == (32, 32)
        assert _outside(im) == set()


def test_water_frames_in_gamut():
    for f in range(3):
        im = terrain.water(f, tile=32, seed=1)
        assert _outside(im) == set()


def test_ground_deterministic():
    a = terrain.ground("grass", 32, seed=5)
    b = terrain.ground("grass", 32, seed=5)
    assert list(a.getdata()) == list(b.getdata())
    c = terrain.ground("grass", 32, seed=6)
    assert list(a.getdata()) != list(c.getdata())  # seed changes result


def test_ground_tiles_are_seamless():
    """Repeating a ground tile must not create a visible seam: the mean
    colour step across the wrap edge should be no worse than a typical
    interior step."""
    for kind in ("grass", "sand", "stone"):
        im = terrain.ground(kind, tile=32, seed=3).convert("RGB")
        a = np.asarray(im, dtype=float)
        # horizontal: interior neighbour diffs vs wrap (last col -> first col)
        interior = np.abs(np.diff(a, axis=1)).mean()
        wrap = np.abs(a[:, -1] - a[:, 0]).mean()
        assert wrap <= interior * 2.5 + 6, (kind, wrap, interior)
        # vertical
        interior_v = np.abs(np.diff(a, axis=0)).mean()
        wrap_v = np.abs(a[-1, :] - a[0, :]).mean()
        assert wrap_v <= interior_v * 2.5 + 6, (kind, wrap_v, interior_v)


def test_nature_props_in_gamut_and_have_content():
    for kind in nature.PROPS:
        im = nature.make(kind, tile=32, seed=2)
        assert im.size == (32, 32)
        assert _outside(im) == set()
        # opaque pixels exist (prop actually drew something)
        opaque = sum(1 for p in im.getdata() if p[3] >= 128)
        assert opaque > 8, kind


def test_nature_deterministic():
    a = nature.make("tree_round", 32, seed=9)
    b = nature.make("tree_round", 32, seed=9)
    assert list(a.getdata()) == list(b.getdata())
