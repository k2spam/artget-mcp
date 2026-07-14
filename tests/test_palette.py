"""M1 acceptance: palette loads, quantization is deterministic and in-gamut."""
import random

from PIL import Image

from artgen import palette


def test_palette_loads():
    cols, tile = palette.load()
    assert tile == 16
    assert len(cols) == 53
    assert all(len(c) == 3 for c in cols)
    # no duplicates
    assert len(set(cols)) == len(cols)


def test_colors_cached_and_hex_roundtrip():
    cols = palette.colors()
    assert len(cols) == 53
    for hx in palette.hex_colors():
        assert palette.hex_to_rgb(hx) in cols


def test_nearest_returns_palette_member():
    for _ in range(200):
        px = (random.randrange(256), random.randrange(256), random.randrange(256))
        assert palette.nearest(px) in palette.colors()


def test_nearest_identity():
    for c in palette.colors():
        assert palette.nearest(c) == c


def test_quantize_deterministic():
    rng = random.Random(1)
    im = Image.new("RGBA", (16, 16))
    px = im.load()
    for y in range(16):
        for x in range(16):
            px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256), 255)
    a = palette.quantize(im)
    b = palette.quantize(im)
    assert list(a.getdata()) == list(b.getdata())


def test_quantize_zero_colors_outside_palette():
    rng = random.Random(2)
    im = Image.new("RGBA", (32, 32))
    px = im.load()
    for y in range(32):
        for x in range(32):
            a = 255 if (x + y) % 3 else 0  # some transparent pixels too
            px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256), a)
    q = palette.quantize(im)
    assert palette.colors_outside(q) == set()


def test_ramp():
    c0, c1 = (0, 0, 0), (10, 20, 30)
    r = palette.ramp(c0, c1, 3)
    assert r[0] == c0 and r[-1] == c1
    assert len(r) == 3
