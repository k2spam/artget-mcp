"""M1: canvas primitives behave and stay deterministic."""
import numpy as np

from artgen import canvas


def test_img_size_and_transparent():
    im = canvas.img(32)
    assert im.size == (32, 32)
    assert im.getpixel((0, 0)) == (0, 0, 0, 0)


def test_from_map_hex_and_transparent():
    rows = ["..", "#ff0000-placeholder"]  # replaced below
    rows = [".X", "X."]
    im = canvas.from_map(rows, {"X": "#ff0000"})
    assert im.getpixel((0, 0)) == (0, 0, 0, 0)
    assert im.getpixel((1, 0)) == (255, 0, 0, 255)
    assert im.getpixel((0, 1)) == (255, 0, 0, 255)


def test_from_map_rejects_nonsquare():
    try:
        canvas.from_map(["XXX", "X"], {"X": "#000000"})
    except ValueError:
        return
    raise AssertionError("expected ValueError on ragged rows")


def test_value_noise_deterministic_and_bounded():
    a = canvas.value_noise(16, 16, seed=7)
    b = canvas.value_noise(16, 16, seed=7)
    assert np.array_equal(a, b)
    assert a.shape == (16, 16)
    assert a.min() >= 0.0 and a.max() <= 1.0
    # different seed -> different field
    c = canvas.value_noise(16, 16, seed=8)
    assert not np.array_equal(a, c)


def test_mirror_x_symmetric():
    im = canvas.img(4)
    im.putpixel((0, 1), (1, 2, 3, 255))
    m = canvas.mirror_x(im)
    assert m.getpixel((0, 1)) == m.getpixel((3, 1))


def test_outline_adds_border():
    im = canvas.img(4)
    im.putpixel((1, 1), (255, 255, 255, 255))
    o = canvas.outline(im, "#000000")
    assert o.getpixel((0, 1))[:3] == (0, 0, 0)
    assert o.getpixel((1, 1)) == (255, 255, 255, 255)


def test_drop_shadow_keeps_sprite():
    im = canvas.img(4)
    im.putpixel((1, 1), (255, 255, 255, 255))
    s = canvas.drop_shadow(im, 1, 1)
    assert s.getpixel((1, 1))[:3] == (255, 255, 255)
    assert s.getpixel((2, 2))[3] > 0  # shadow present at offset
