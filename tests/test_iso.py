"""Iso prototype checks: window-in-wall validation, in-gamut assets."""
from artgen import iso, palette


def test_plan_windows_within_wall():
    """Windows must never exceed the wall bounds (with frame margin)."""
    fr = 0.14
    for umax in (1.6, 2.0, 2.8, 4.0):
        for wh in (1.2, 1.5, 2.4):
            for n in (1, 2, 3):
                for (uc, zc, w, h) in iso.plan_windows(umax, wh, n):
                    assert uc - w / 2 - fr >= -1e-6, (umax, wh, n, uc)
                    assert uc + w / 2 + fr <= umax + 1e-6, (umax, wh, n, uc)
                    assert zc - h / 2 - fr >= -1e-6
                    assert zc + h / 2 + fr <= wh + 1e-6


def test_plan_windows_tiny_wall_empty():
    assert iso.plan_windows(0.6, 0.6, 3) == []


def test_houses_in_gamut():
    for walls in iso.WALL_MATERIALS:
        for roof in iso.ROOF_TYPES:
            im, ax, ay = iso.house(walls, roof, seed=1)
            assert palette.colors_outside(im) == set(), (walls, roof)


def test_terrain_water_props_in_gamut():
    for k in iso.BIOMES:
        im = iso.diamond(k, seed=1)
        assert palette.colors_outside(im) == set(), k
    assert palette.colors_outside(iso.water_tile(0, foam={"NE", "SW"})) == set()
    for fn in (iso.tree, iso.conifer):
        im, _, _ = fn(seed=1)
        assert palette.colors_outside(im) == set()


def test_coast_tile_in_gamut_and_seamless_corners():
    # every corner config renders in-gamut
    for m in range(16):
        corners = tuple(bool(m & (1 << k)) for k in range(4))
        im = iso.coast_tile(corners, seed=3)
        assert palette.colors_outside(im) == set(), corners
    # all-land -> land diamond; all-water -> water tile
    assert iso.coast_tile((0, 0, 0, 0), seed=1).size == iso.diamond("grass", 1).size
    assert iso.coast_tile((1, 1, 1, 1), seed=1).size == iso.water_tile(0).size


def test_two_storey_windows_within_walls():
    # 2-storey uses two window rows; both must stay within the wall
    import artgen.iso as I
    for zc in (2.6 * 0.26, 2.6 * 0.72):
        for (uc, zz, w, h) in I.plan_windows(2.0, 2.6, 3, zc=zc):
            assert uc - w / 2 - 0.14 >= -1e-6 and uc + w / 2 + 0.14 <= 2.0 + 1e-6
            assert zz - h / 2 - 0.14 >= -1e-6 and zz + h / 2 + 0.14 <= 2.6 + 1e-6


def test_house_deterministic():
    a = iso.house("log", "red", seed=5)[0]
    b = iso.house("log", "red", seed=5)[0]
    assert a.tobytes() == b.tobytes()
