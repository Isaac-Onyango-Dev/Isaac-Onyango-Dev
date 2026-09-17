#!/usr/bin/env python3
"""
Draws the animated profile banner, assets/header.svg.

The banner is a committed asset rather than a call to a rendering service, so
it keeps working no matter which free SVG host goes offline. Re-run this only
when the wording or the artwork changes.

    python scripts/build_header.py
"""

from __future__ import annotations

import math
from pathlib import Path

W, H = 1012, 290

# The pill label is stretched to exactly PILL_TEXT wide, so the capsule
# fits whichever font the viewer's machine substitutes.
PILL_TEXT = 196
PILL_W = 88 + PILL_TEXT + 14 - 60.5

BLUE = "#58a6ff"
DEEP = "#1f6feb"
AMBER = "#f0883e"
TEXT = "#e6edf3"
MUTED = "#8b949e"


SECONDS_PER_TOOTH = 2.0  # a gear with N teeth turns once every 2N seconds

# Shared by every SVG: one spin keyframe, switched off for reduced motion.
MOTION_CSS = """
    .spin { transform-box: fill-box; transform-origin: center;
            animation: spin linear infinite; }
    .ccw  { animation-direction: reverse; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) {
      .spin, .sweep { animation: none; }
    }"""


def tooth_outline(teeth: int, module: float) -> list[tuple[float, float]]:
    """Gear outline in polar-free x/y, one tooth centred on angle 0.

    module is the tooth size. Gears only mesh when they share it: the pitch
    radius is module * teeth / 2, so neighbours sit exactly one pitch radius
    apart. Teeth are about 37% of the circular pitch; the straight flanks are
    not true involutes, so this backlash is what keeps them from overlapping
    (scripts/test_build_header.py proves it over a full turn).
    """
    pitch = module * teeth / 2
    tip, root = pitch + module, pitch - 1.25 * module
    step = 2 * math.pi / teeth
    points = []
    for index in range(teeth):
        centre = index * step
        for offset, radius in ((-0.27, root), (-0.12, tip), (0.12, tip), (0.27, root)):
            angle = centre + offset * step
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def gear_train(origin: tuple[float, float], module: float,
               specs: list[tuple[int, str, int | None, float]]) -> list[dict]:
    """Place meshing gears.

    Each spec is (teeth, colour, index of the gear it meshes with, direction
    in degrees from that gear's centre). The first gear is the driver. Every
    other gear is positioned one pitch-radius sum away, spins the opposite way
    to its partner at the tooth ratio, and is phased so a gap faces each tooth.
    """
    gears: list[dict] = []
    for teeth, colour, parent, direction in specs:
        if parent is None:
            gears.append({"teeth": teeth, "colour": colour, "x": origin[0], "y": origin[1],
                          "phase": 0.0, "ccw": False})
            continue
        p = gears[parent]
        theta = math.radians(direction)
        distance = module * (p["teeth"] + teeth) / 2
        p_step, step = 2 * math.pi / p["teeth"], 2 * math.pi / teeth
        # How far past its nearest tooth the partner is at the contact line,
        # as a fraction of one tooth pitch. The new gear mirrors it, half a pitch on.
        lag = ((theta - p["phase"]) % p_step) / p_step
        gears.append({
            "teeth": teeth, "colour": colour,
            "x": p["x"] + distance * math.cos(theta),
            "y": p["y"] + distance * math.sin(theta),
            "phase": theta + math.pi + (lag - 0.5) * step,
            "ccw": not p["ccw"],
        })
    for g in gears:
        g["module"] = module
    return gears


def draw_gear(g: dict, opacity: float) -> str:
    module, teeth, colour = g["module"], g["teeth"], g["colour"]
    pitch = module * teeth / 2
    hub = max(pitch * 0.34, module * 1.6)
    outline = " L ".join(f"{x:.2f},{y:.2f}" for x, y in tooth_outline(teeth, module))
    spin = "spin ccw" if g["ccw"] else "spin"
    web_r = pitch - 3.2 * module
    web = (f'<circle r="{web_r:.2f}" fill="none" stroke="{colour}" '
           f'stroke-opacity="0.35" stroke-width="1.2"/>') if web_r > hub + module else ""
    # The invisible circle pins the bounding box to the gear centre, so
    # transform-origin: center is the true axle whatever the tooth phase.
    return f"""
  <g transform="translate({g['x']:.2f} {g['y']:.2f}) rotate({math.degrees(g['phase']):.3f})"
     opacity="{opacity}">
    <g class="{spin}" style="animation-duration:{teeth * SECONDS_PER_TOOTH:g}s">
      <circle r="{pitch + module + 1:.2f}" fill="none"/>
      <path d="M {outline} Z" fill="{colour}" fill-opacity="0.07" stroke="{colour}"
            stroke-width="2" stroke-linejoin="round"/>
      {web}
      <circle r="{hub:.2f}" fill="none" stroke="{colour}" stroke-width="2"/>
      <rect x="{-module * 0.45:.2f}" y="{-hub - module * 0.2:.2f}" width="{module * 0.9:.2f}"
            height="{module * 0.9:.2f}" rx="{module * 0.2:.2f}" fill="{colour}" fill-opacity="0.8"/>
      <circle r="{hub * 0.38:.2f}" fill="{colour}" fill-opacity="0.55"/>
    </g>
  </g>"""


def build_footer() -> str:
    fw, fh = 1012, 108
    pair = "".join(
        draw_gear(g, 0.55)
        for g in gear_train((944, 54), 4, [(18, BLUE, None, 0), (11, AMBER, 0, 180)])
    )
    teeth = "".join(
        f'<rect x="{44 + i * 24}" y="{fh - 16}" width="9" height="2" rx="1" '
        f'fill="{AMBER}" fill-opacity="{0.32 - i * 0.0075:.3f}"/>'
        for i in range(40)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{fw}" height="{fh}"
     viewBox="0 0 {fw} {fh}" role="img" aria-label="Build it manually. Understand it deeply. Ship it cleanly.">
  <title>Build it manually. Understand it deeply. Ship it cleanly.</title>
  <style>{MOTION_CSS}
  </style>
  <defs>
    <linearGradient id="fbg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#131a24"/>
      <stop offset="55%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#07111f"/>
    </linearGradient>
    <pattern id="fgrid" width="34" height="34" patternUnits="userSpaceOnUse">
      <path d="M34 0H0V34" fill="none" stroke="{BLUE}" stroke-opacity="0.05" stroke-width="1"/>
    </pattern>
    <clipPath id="fframe"><rect width="{fw}" height="{fh}" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#fframe)">
    <rect width="{fw}" height="{fh}" fill="url(#fbg)"/>
    <rect width="{fw}" height="{fh}" fill="url(#fgrid)"/>
{pair}
    <text x="44" y="52" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="19"
          font-weight="700" fill="{TEXT}">Build it manually. Understand it deeply. <tspan
          fill="{BLUE}">Ship it cleanly.</tspan></text>
    <text x="44" y="76" font-family="Consolas,monospace" font-size="12" fill="{MUTED}">
      GEARS &#183; Nairobi, Kenya &#183; isaaco62800@gmail.com
    </text>
{teeth}
    <rect x="0.75" y="0.75" width="{fw - 1.5}" height="{fh - 1.5}" rx="18" fill="none"
          stroke="{DEEP}" stroke-opacity="0.4" stroke-width="1.5"/>
  </g>
</svg>
"""


def main() -> None:
    # One driver, two followers. Positions and phases come from the train,
    # so the teeth genuinely mesh and the speeds follow the tooth ratios.
    gears = "".join(
        draw_gear(g, 0.9)
        for g in gear_train((848, 138), 6, [
            (24, BLUE, None, 0),
            (14, AMBER, 0, 40),
            (10, DEEP, 0, 135),
        ])
    )

    ticks = "".join(
        f'<rect x="{60 + i * 26}" y="{H - 26}" width="10" height="2" rx="1" '
        f'fill="{BLUE}" fill-opacity="{0.30 - i * 0.008:.3f}"/>'
        for i in range(30)
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="Isaac Onyango — full-stack developer">
  <title>Isaac Onyango — Full-Stack Developer, Nairobi, Kenya</title>
  <style>{MOTION_CSS}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#07111f"/>
      <stop offset="46%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#131a24"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{AMBER}"/>
      <stop offset="100%" stop-color="{DEEP}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.82" cy="0.4" r="0.55">
      <stop offset="0%" stop-color="{DEEP}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{DEEP}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="blueprint" width="34" height="34" patternUnits="userSpaceOnUse">
      <path d="M34 0H0V34" fill="none" stroke="{BLUE}" stroke-opacity="0.055" stroke-width="1"/>
    </pattern>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#blueprint)"/>
    <rect width="{W}" height="{H}" fill="url(#glow)"/>
{gears}

    <g font-family="Segoe UI,Helvetica,Arial,sans-serif">
      <g>
        <rect x="60.5" y="46.5" width="{PILL_W}" height="27" rx="13.5" fill="{AMBER}"
              fill-opacity="0.08" stroke="{AMBER}" stroke-opacity="0.35"/>
        <circle cx="76" cy="60" r="3" fill="{AMBER}"/>
        <text x="88" y="64.2" font-size="11.5" font-weight="600" fill="{AMBER}"
              textLength="{PILL_TEXT}" lengthAdjust="spacingAndGlyphs">GEARS · SOFTWARE THAT FITS</text>
      </g>

      <text x="58" y="146" font-size="56" font-weight="800" letter-spacing="-0.5"
            fill="#ffffff">ISAAC <tspan fill="{BLUE}">ONYANGO</tspan></text>

      <rect x="60" y="164" width="300" height="3" rx="1.5" fill="url(#rule)"/>

      <text x="60" y="200" font-size="16.5" fill="{TEXT}" letter-spacing="0.4">
        Full-Stack Developer &#183; Open-Source Builder &#183; Digital Creator
      </text>
      <text x="60" y="228" font-family="Consolas,monospace" font-size="13" fill="{MUTED}">
        Nairobi, Kenya &#160;|&#160; TypeScript &#183; Python &#183; React &#183; FastAPI &#183; Electron
      </text>
    </g>
    {ticks}
    <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="none"
          stroke="{DEEP}" stroke-opacity="0.45" stroke-width="1.5"/>
  </g>
</svg>
"""
    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for name, body in (("header.svg", svg), ("footer.svg", build_footer())):
        (assets / name).write_text(body, encoding="utf-8")
        print(f"wrote assets/{name}")


if __name__ == "__main__":
    main()
