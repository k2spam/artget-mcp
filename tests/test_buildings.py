"""M4 acceptance: houses (all combos) + props are in-gamut, deterministic,
and fences tile horizontally."""
import numpy as np

from artgen import palette
from artgen.procgen import buildings as B


def _outside(im):
    return palette.colors_outside(im)


def test_all_house_combos_in_gamut():
    for size in B.SIZES:
        for roof in B.ROOFS:
            for walls in B.WALLS:
                im = B.house(size, roof, walls, seed=1)
                assert _outside(im) == set(), (size, roof, walls)
                # actually drew something substantial
                opaque = sum(1 for p in im.getdata() if p[3] >= 128)
                assert opaque > 100, (size, roof, walls, opaque)


def test_house_sizes_grow():
    s = B.house("S", "slate", "timber").size[0]
    m = B.house("M", "slate", "timber").size[0]
    l = B.house("L", "slate", "timber").size[0]
    assert s < m < l


def test_house_deterministic():
    a = B.house("M", "red", "stone", seed=5)
    b = B.house("M", "red", "stone", seed=5)
    assert list(a.getdata()) == list(b.getdata())


def test_bad_params_raise():
    for kw in (dict(size="XL"), dict(roof="gold"), dict(walls="glass")):
        try:
            B.house(**kw)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {kw}")


def test_all_props_in_gamut_and_have_content():
    for kind in B.PROPS:
        im = B.make_prop(kind, seed=2)
        assert _outside(im) == set(), kind
        opaque = sum(1 for p in im.getdata() if p[3] >= 128)
        assert opaque > 20, kind


def test_fence_tiles_horizontally():
    """Rails must reach both side edges so adjacent segments connect."""
    f = B.fence(gate=False, tile=32, seed=1)
    a = np.asarray(f.convert("RGBA"))
    left = a[:, 0, 3] >= 128
    right = a[:, -1, 3] >= 128
    # the rail rows that are opaque on the left must also be opaque on the right
    assert left.any() and right.any()
    assert np.array_equal(left, right), "fence rails do not line up across the seam"


def test_catalog_covers_props_and_houses():
    cat = B.catalog(seed=3)
    assert any(k.startswith("house_") for k in cat)
    for p in B.PROPS:
        assert p in cat
