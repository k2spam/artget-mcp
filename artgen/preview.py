"""Preview helpers: contact sheets and tileable checks.

A contact sheet arranges tiles in a grid, scaled up with NEAREST so pixels
stay crisp, on a neutral checker background so transparency is visible. Also
provides base64 encoding for showing results inline (used by the MCP layer).
"""
from __future__ import annotations

import base64
import io
from typing import Iterable

from PIL import Image, ImageDraw

_BG_A = (58, 58, 68, 255)   # #3a3a44
_BG_B = (86, 80, 97, 255)   # #565061


def _checker(w: int, h: int, cell: int = 8) -> Image.Image:
    im = Image.new("RGBA", (w, h), _BG_A)
    d = ImageDraw.Draw(im)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=_BG_B)
    return im


def contact_sheet(tiles: Iterable[Image.Image], cols: int = 8, scale: int = 4,
                  pad: int = 4) -> Image.Image:
    """Grid of tiles scaled by `scale`, padded, on a checker background."""
    tiles = [t.convert("RGBA") for t in tiles]
    if not tiles:
        return Image.new("RGBA", (1, 1))
    tw, th = tiles[0].size
    cw, ch = tw * scale, th * scale
    cols = max(1, min(cols, len(tiles)))
    rows = (len(tiles) + cols - 1) // cols
    W = cols * cw + (cols + 1) * pad
    H = rows * ch + (rows + 1) * pad
    sheet = _checker(W, H)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + pad)
        sheet.alpha_composite(t.resize((cw, ch), Image.NEAREST), (x, y))
    return sheet


def to_b64(im: Image.Image) -> str:
    """PNG bytes of an image as a base64 string (for inline preview)."""
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def sheet_b64(tiles: Iterable[Image.Image], **kw) -> str:
    return to_b64(contact_sheet(tiles, **kw))


def tile_3x3(tile: Image.Image) -> Image.Image:
    """Repeat a tile 3x3 to eyeball seamlessness of a repeating ground tile."""
    t = tile.convert("RGBA")
    w, h = t.size
    out = Image.new("RGBA", (w * 3, h * 3))
    for j in range(3):
        for i in range(3):
            out.alpha_composite(t, (i * w, j * h))
    return out
