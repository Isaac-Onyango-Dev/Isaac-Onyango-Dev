"""Run with: python scripts/test_build_header.py

Spins each gear train through a full cycle, exactly as the CSS animation
does, and checks that meshing teeth never cut into each other and that
they really are engaged rather than just sitting close.
"""

import math

from build_header import AMBER, BLUE, DEEP, SECONDS_PER_TOOTH, gear_train, tooth_outline


def posed(g, t):
    turn = 2 * math.pi * t / (g["teeth"] * SECONDS_PER_TOOTH)
    a = g["phase"] + (-turn if g["ccw"] else turn)
    c, s = math.cos(a), math.sin(a)
    pts = tooth_outline(g["teeth"], g["module"])
    return [(g["x"] + x * c - y * s, g["y"] + x * s + y * c) for x, y in pts]


def inside(pt, poly):
    x, y, hit = *pt, False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def densify(poly, n=6):
    return [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n)
            for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]) for k in range(n)]


def check(train):
    driver = train[0]
    cycle = driver["teeth"] * SECONDS_PER_TOOTH
    for follower in train[1:]:
        m = follower["module"]
        gap = math.dist((driver["x"], driver["y"]), (follower["x"], follower["y"]))
        # Tips must reach past the partner's pitch circle, or nothing is driving anything.
        reach = m * (driver["teeth"] + follower["teeth"]) / 2 + 2 * m
        assert reach - gap > 1.5 * m, f"{follower['teeth']}T gear is not engaged"
        # The follower's tooth ratio makes it complete whole turns in step with the driver.
        assert follower["ccw"] != driver["ccw"], "meshing gears must counter-rotate"
        for step in range(240):
            t = cycle * step / 240
            a, b = posed(driver, t), posed(follower, t)
            clash = [p for p in densify(b) if inside(p, a)]
            assert not clash, f"{follower['teeth']}T clashes with driver at t={t:.2f}s"


if __name__ == "__main__":
    check(gear_train((848, 138), 6, [(24, BLUE, None, 0), (14, AMBER, 0, 40), (10, DEEP, 0, 135)]))
    check(gear_train((944, 54), 4, [(18, BLUE, None, 0), (11, AMBER, 0, 180)]))

    # Sanity check the check: a follower rotated half a tooth out of phase must clash.
    bad = gear_train((0, 0), 5, [(24, BLUE, None, 0), (14, AMBER, 0, 35)])
    bad[1]["phase"] += math.pi / 14
    try:
        check(bad)
    except AssertionError:
        print("ok")
    else:
        raise SystemExit("mesh check failed to catch a misaligned gear")
