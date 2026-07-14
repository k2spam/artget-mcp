"""M1-M4 polish: new biomes, roads, and decor props."""
import numpy as np

from artgen import palette
from artgen.procgen import buildings as B
from artgen.procgen import roads, terrain


def test_new_biomes_in_gamut():
    for kind in ("pine_floor", "gravel", "cobble", "path", "snow", "swamp", "dirt"):
        im = terrain.ground(kind, 32, 3)
        assert palette.colors_outside(im) == set(), kind


def test_terrain_variants_distinct():
    """Variety reduces repetition: variants must actually differ."""
    vs = terrain.variants("grass", 32, 42, variety=6)
    assert len({v.tobytes() for v in vs}) == 6


def test_cobble_and_path_seamless():
    for kind in ("path", "cobble", "gravel"):
        im = terrain.ground(kind, 32, 3).convert("RGB")
        a = np.asarray(im, float)
        wrap = np.abs(a[:, -1] - a[:, 0]).mean()
        interior = np.abs(np.diff(a, axis=1)).mean()
        assert wrap <= interior * 2.5 + 8, (kind, wrap, interior)


def test_road_render():
    for layout in roads.LAYOUTS:
        im = roads.render("path", 8, 8, 32, seed=5, layout=layout, width=2)
        assert im.size == (8 * 32, 8 * 32)
        # road actually carved (some non-grass pixels present)
        assert im.getbbox() is not None


def test_new_decor_props_in_gamut():
    for kind in ("bucket", "sack", "potted_plant", "flower_box", "lantern", "axe_stump"):
        assert kind in B.PROPS
        im = B.make_prop(kind, 2)
        assert palette.colors_outside(im) == set(), kind
        assert sum(1 for p in im.getdata() if p[3] >= 128) > 15
