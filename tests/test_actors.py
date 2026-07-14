"""Stage 6: actors are in-gamut, deterministic, and actually animate."""
from artgen import iso_actors as A
from artgen import palette


def test_roster_in_gamut_all_dirs():
    for name in A.ROSTER:
        for dr in A.DIRS:
            im, ax, ay = A.make(name, dr, 0, seed=2)
            assert palette.colors_outside(im) == set(), (name, dr)
            assert sum(1 for p in im.getdata() if p[3] >= 128) > 20, name


def test_walk_frames_differ():
    for name in ("villager", "wolf", "slime", "skeleton", "deer"):
        frames = [A.make(name, "E", f, seed=1)[0].tobytes() for f in range(4)]
        assert len(set(frames)) >= 2, name  # animation actually moves


def test_all_four_directions_distinct():
    # front / back / side should be visibly different sprites
    for name in ("villager", "wolf", "deer"):
        views = {A.make(name, d, 1, seed=1)[0].tobytes() for d in ("S", "N", "E")}
        assert len(views) == 3, name


def test_deterministic_and_random_variation():
    a = A.person("villager", "SE", 0, seed=7)[0].tobytes()
    b = A.person("villager", "SE", 0, seed=7)[0].tobytes()
    assert a == b
    variants = {A.person("villager", "SE", 0, seed=s)[0].tobytes() for s in range(12)}
    assert len(variants) >= 6  # seeds produce visibly different villagers


def test_direction_mirror():
    e = A.make("wolf", "E", 0, seed=1)[0]
    w = A.make("wolf", "W", 0, seed=1)[0]
    assert e.tobytes() != w.tobytes()
