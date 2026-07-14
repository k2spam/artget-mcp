#!/usr/bin/env python3
"""Generate CC0 pixel-art assets for Heroquarium (16x16 tiles & sprites)."""
import os, random
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'assets')
os.makedirs(OUT, exist_ok=True)
random.seed(42)

T = 16  # tile size

def img():
    return Image.new('RGBA', (T, T), (0, 0, 0, 0))

def hex2rgba(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def from_map(rows, pal):
    """rows: 16 strings of 16 chars; pal: char -> hex or None."""
    im = img()
    assert len(rows) == T, f'rows={len(rows)}'
    for y, row in enumerate(rows):
        assert len(row) == T, f'row {y} len={len(row)}: {row}'
        for x, ch in enumerate(row):
            if ch == '.':
                continue
            c = pal[ch]
            if c is None:
                continue
            im.putpixel((x, y), hex2rgba(c))
    return im

def ground(base, light, dark, dots=14, seed=0):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (T, T), hex2rgba(base))
    for _ in range(dots):
        x, y = rnd.randrange(T), rnd.randrange(T)
        im.putpixel((x, y), hex2rgba(light if rnd.random() < .5 else dark))
    return im

def save(im, name):
    im.save(os.path.join(OUT, name + '.png'))

O = '#241d2b'  # outline

# ---------- ground tiles ----------
save(ground('#4f7a3a', '#5f8f46', '#446a32', seed=1), 'grass0')
save(ground('#4f7a3a', '#5f8f46', '#446a32', seed=2), 'grass1')
g = ground('#4f7a3a', '#5f8f46', '#446a32', seed=3)
for (x, y, c) in [(4, 5, '#e3d05a'), (11, 9, '#d97b7b'), (7, 12, '#e8e4dc')]:
    g.putpixel((x, y), hex2rgba(c))
save(g, 'grass_flowers')
save(ground('#3e6631', '#4a7a3a', '#345527', seed=4), 'forest_floor')
save(ground('#d9c07f', '#e3cf94', '#c4a86a', seed=5), 'sand0')
save(ground('#d9c07f', '#e3cf94', '#c4a86a', seed=6), 'sand1')

def water(seed):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (T, T), hex2rgba('#2f5e8f'))
    for _ in range(10):
        x, y = rnd.randrange(T), rnd.randrange(T)
        im.putpixel((x, y), hex2rgba('#3f75ad'))
    for _ in range(3):
        x, y = rnd.randrange(1, T - 3), rnd.randrange(T)
        for dx in range(3):
            im.putpixel((x + dx, y), hex2rgba('#7fa8cc'))
    return im
save(water(7), 'water0')
save(water(8), 'water1')

save(ground('#6a6475', '#7a7485', '#565061', dots=18, seed=9), 'rock_floor')

# ---------- tree ----------
tree = from_map([
    '................',
    '.....OOOOO......',
    '...OODDDDDOO....',
    '..ODDFDDDDDDO...',
    '..ODFFDDFDDDO...',
    '.ODDDDDDDDDDDO..',
    '.ODFDDDFDDDFDO..',
    '.ODDDDDDDDDDDO..',
    '..ODDFDDDDFDO...',
    '..OODDDDDDDOO...',
    '....OODDDOO.....',
    '.....OTTO.......',
    '.....OTTO.......',
    '....OTTTTO......',
    '.....OOOO.......',
    '................',
], {'O': O, 'D': '#2f5a2b', 'F': '#417a37', 'T': '#6e4a2f'})
save(tree, 'tree')

# ---------- cactus ----------
cactus = from_map([
    '................',
    '......OO........',
    '.....OCCO.......',
    '.....OCLO.......',
    '..OO.OCCO.OO....',
    '.OCCOOCCOOCCO...',
    '.OCCOCCCOCLCO...',
    '.OCCCCCCCCCCO...',
    '..OOCCCLCCOO....',
    '....OCCCCO......',
    '.....OCCO.......',
    '.....OCCO.......',
    '.....OCCO.......',
    '....OOCCOO......',
    '................',
    '................',
], {'O': O, 'C': '#4a8f4a', 'L': '#5fa85f'})
save(cactus, 'cactus')

# ---------- rock ----------
rock = from_map([
    '................',
    '................',
    '................',
    '......OOO.......',
    '....OORRROO.....',
    '...ORRLRRRRO....',
    '..ORRLLRRRRRO...',
    '..ORLRRRRDRRO...',
    '.ORRRRRRRDDRRO..',
    '.ORRRRRDDDRRRO..',
    '.ORRRRRRRRRRDO..',
    '..ORRDDRRRDDO...',
    '...OODDDDDOO....',
    '.....OOOOO......',
    '................',
    '................',
], {'O': O, 'R': '#7a7485', 'L': '#948da3', 'D': '#565061'})
save(rock, 'rock')

# ---------- house (town tile) ----------
house = from_map([
    '................',
    '......OO........',
    '....OORROO......',
    '...ORRRRRRO.....',
    '..ORRLRRRRRO....',
    '.ORRRRRRRLRRO...',
    'ORRRRRRRRRRRRO..',
    'OOOOOOOOOOOOOO..',
    '.OWWWWWWWWWWO...',
    '.OWWGGWWWWWWO...',
    '.OWWGGWWDDWWO...',
    '.OWWWWWWDDWWO...',
    '.OWWWWWWDDWWO...',
    '.OOOOOOOOOOOO...',
    '................',
    '................',
], {'O': O, 'R': '#b55a33', 'L': '#cc7444', 'W': '#cbb08a', 'G': '#ffd982', 'D': '#5a3a24'})
save(house, 'house')

# ---------- tent (mob camp) ----------
tent = from_map([
    '................',
    '................',
    '................',
    '.......O........',
    '......OTO.......',
    '.....OTTLO......',
    '.....OTTLO......',
    '....OTTTLLO.....',
    '....OTTTLLO.....',
    '...OTTTTLLLO....',
    '...OTTDDTLLO....',
    '..OTTTDDTTLLO...',
    '..OTTTDDTTLLO...',
    '..OOOOOOOOOOO...',
    '................',
    '................',
], {'O': O, 'T': '#b0623a', 'L': '#8f4f2f', 'D': '#3a2417'})
save(tent, 'tent')

# ---------- chibi template ----------
CHIBI = [
    '................',
    '...OOOOOOOOOO...',
    '..OHHHHHHHHHHO..',
    '..OHHHHHHHHHHO..',
    '..OHHHHHHHHHHO..',
    '..OHSSSSSSSSHO..',
    '..OSSESSSSESSO..',
    '..OSSSSSSSSSSO..',
    '...OSSSSSSSSO...',
    '....OTTTTTTO....',
    '...OSTTTTTTSO...',
    '...OSTATTATSO...',
    '....OTTTTTTO....',
    '....OPPPPPPO....',
    '....OBBOOBBO....',
    '................',
]

def chibi(hair, skin, shirt, pants, boots, accent=None, eye='#241d2b'):
    return from_map(CHIBI, {
        'O': O, 'H': hair, 'S': skin, 'E': eye, 'T': shirt,
        'A': accent or shirt, 'P': pants, 'B': boots,
    })

save(chibi('#7a4a2a', '#e8b088', '#e8e4dc', '#4a5a8f', '#3a2a1a', accent='#c9c2b5'), 'hero')
save(chibi('#3a3a44', '#d8a878', '#8f5a3a', '#4a3a2a', '#241d2b', accent='#e8c15a'), 'trader')

# ---------- mobs ----------
slime = from_map([
    '................',
    '................',
    '................',
    '................',
    '................',
    '................',
    '......OOOO......',
    '....OOGGGGOO....',
    '...OGGLGGGGGO...',
    '..OGGLLGGGGGGO..',
    '..OGGGGGGGGGGO..',
    '.OGGEGGGGEGGGGO.',
    '.OGGEGGGGEGGGGO.',
    '.OGGGGGGGGGGGGO.',
    '..OOOOOOOOOOOO..',
    '................',
], {'O': O, 'G': '#5aa843', 'L': '#7cc45e', 'E': '#241d2b'})
save(slime, 'mob_slime')

boar = from_map([
    '................',
    '................',
    '................',
    '................',
    '................',
    '....OOOOOOO.....',
    '...OBBBBBBBO....',
    '..OBBLBBBBBBOO..',
    '.OBBBBBBBBBBBBO.',
    '.OBEBBBBBBBLBBO.',
    '.OBBBSSOBBBBBBO.',
    '.OBBBSSOBBBBBBO.',
    '..OBBOOBBOBBO...',
    '..OBBO..OBBO....',
    '...OO....OO.....',
    '................',
], {'O': O, 'B': '#7a5238', 'L': '#94684a', 'S': '#e8c8a8', 'E': '#241d2b'})
save(boar, 'mob_boar')

scorpion = from_map([
    '................',
    '................',
    '................',
    '......OO........',
    '.....ORRO.......',
    '......ORRO......',
    '.......ORO......',
    '.OO....ORO..OO..',
    'ORRO..ORRRO.ORRO',
    'ORRO.ORRRRRO.ORO',
    '.ORROORLRRROORO.',
    '..ORRRRRRRRRRO..',
    '...OORRERRROO...',
    '.....ORRRO......',
    '......OOO.......',
    '................',
], {'O': O, 'R': '#b0453a', 'L': '#cc6452', 'E': '#241d2b'})
save(scorpion, 'mob_scorpion')

skeleton = from_map(CHIBI, {
    'O': O, 'H': '#e8e8e0', 'S': '#e8e8e0', 'E': '#241d2b',
    'T': '#c8c8c0', 'A': '#a8a8a0', 'P': '#c8c8c0', 'B': '#e8e8e0',
})
save(skeleton, 'mob_skeleton')

print('assets written to', OUT)
for f in sorted(os.listdir(OUT)):
    print(' ', f)
