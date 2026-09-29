"""Regenera las texturas pixel-art de app/static/img/ (requiere pillow).

Uso: .venv/bin/python scripts/gen_textures.py
"""
import random
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "img"
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(42)


def noise_tile(base, variants, size=64, px=4):
    """Tile de ruido pixelado: celdas de px*px con tonos aleatorios."""
    img = Image.new("RGB", (size, size), base)
    cells = size // px
    for cy in range(cells):
        for cx in range(cells):
            c = rng.choice(variants)
            for y in range(cy * px, (cy + 1) * px):
                for x in range(cx * px, (cx + 1) * px):
                    img.putpixel((x, y), c)
    return img


dirt = noise_tile(
    (121, 85, 58),
    [(121, 85, 58), (109, 76, 51), (133, 94, 64), (98, 68, 45), (121, 85, 58)],
)
dirt.save(OUT / "dirt.png")

stone = noise_tile(
    (107, 107, 107),
    [(107, 107, 107), (96, 96, 96), (118, 118, 118), (88, 88, 88)],
)
stone.save(OUT / "stone.png")

grass = noise_tile(
    (121, 85, 58),
    [(121, 85, 58), (109, 76, 51), (133, 94, 64), (98, 68, 45)],
)
greens = [(93, 156, 58), (84, 143, 52), (103, 168, 64), (76, 130, 47)]
for y in range(16):
    for x in range(64):
        grass.putpixel((x, y), rng.choice(greens))
for x in range(64):
    for y in range(16, 16 + rng.randint(0, 6)):
        grass.putpixel((x, y), rng.choice(greens))
grass.save(OUT / "grass_side.png")

grass_top = noise_tile(
    (93, 156, 58),
    [(93, 156, 58), (84, 143, 52), (103, 168, 64), (76, 130, 47)],
    size=32,
    px=2,
)
grass_top.save(OUT / "grass_top.png")

grass.resize((16, 16), Image.NEAREST).save(OUT / "favicon.png")

print("OK:", sorted(p.name for p in OUT.glob("*.png")))
