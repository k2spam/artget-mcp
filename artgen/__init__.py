"""Heroquarium ArtGen — pixel-art asset generation pipeline.

Components:
- palette : canonical palette (single source of truth = palette.json at repo root)
- canvas  : low-level pixel primitives (pixel-maps, noise, dither, shadow, outline)
- pixelize: normalize any external art to the game palette + tile size
- procgen : procedural tile/sprite generators (later milestones)

Conventions (see ARTGEN_BLUEPRINT.md):
- Generate at TILE=32, export downscaled to 16 for the current renderer.
- RGBA, binary alpha (threshold 128), light from top-left.
"""

__version__ = "0.1.0"

# Canonical generation tile size. Export downsamples to 16 for the game.
TILE = 32
EXPORT_TILE = 16
