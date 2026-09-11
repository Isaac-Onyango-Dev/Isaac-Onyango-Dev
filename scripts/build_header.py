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

BLUE = "#58a6ff"
DEEP = "#1f6feb"
AMBER = "#f0883e"
TEXT = "#e6edf3"
MUTED = "#8b949e"


def gear_path(teeth: int, r_out: float, r_root: float) -> str:
    """Symmetric involute-ish gear outline centred on the origin."""
    step = 2 * math.pi / teeth
    flank = step * 0.12
    land = step * 0.26
    points: list[tuple[float, float]] = []
    for index in range(teeth):
        base = index * step
        for angle, radius in (
            (base, r_root),
            (base + flank, r_out),
            (base + flank + land, r_out),
            (base + 2 * flank + land, r_root),
            (base + step / 2 + land / 2, r_root),
        ):
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
    body = " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f"M {body} Z"


def gear(cx: float, cy: float, teeth: int, r_out: float, r_root: float,
         hole: float, colour: str, opacity: float, seconds: float,
         reverse: bool = False) -> str:
    start, end = (0, 360) if not reverse else (360, 0)
    return f"""
  <g transform="translate({cx} {cy})" opacity="{opacity}">
    <g>
      <path d="{gear_path(teeth, r_out, r_root)}" fill="none" stroke="{colour}" stroke-width="2.2"
            stroke-linejoin="round"/>
      <circle r="{hole:.1f}" fill="none" stroke="{colour}" stroke-width="2.2"/>
      <circle r="{hole * 0.32:.1f}" fill="{colour}" fill-opacity="0.5"/>
      <animateTransform attributeName="transform" type="rotate"
        from="{start} 0 0" to="{end} 0 0" dur="{seconds}s" repeatCount="indefinite"/>
    </g>
  </g>"""


def build_footer() -> str:
    fw, fh = 1012, 108
    teeth = "".join(
        f'<rect x="{44 + i * 24}" y="{fh - 16}" width="9" height="2" rx="1" '
        f'fill="{AMBER}" fill-opacity="{0.32 - i * 0.0075:.3f}"/>'
        for i in range(40)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{fw}" height="{fh}"
     viewBox="0 0 {fw} {fh}" role="img" aria-label="Build it manually. Understand it deeply. Ship it cleanly.">
  <title>Build it manually. Understand it deeply. Ship it cleanly.</title>
  <defs>
    <linearGradient id="fbg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#131a24"/>
      <stop offset="55%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#07111f"/>
    </linearGradient>
    <linearGradient id="fink" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{AMBER}"/>
      <stop offset="100%" stop-color="{BLUE}"/>
    </linearGradient>
    <pattern id="fgrid" width="34" height="34" patternUnits="userSpaceOnUse">
      <path d="M34 0H0V34" fill="none" stroke="{BLUE}" stroke-opacity="0.05" stroke-width="1"/>
    </pattern>
    <clipPath id="fframe"><rect width="{fw}" height="{fh}" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#fframe)">
    <rect width="{fw}" height="{fh}" fill="url(#fbg)"/>
    <rect width="{fw}" height="{fh}" fill="url(#fgrid)"/>
{gear(930, 54, 11, 46, 35, 16, BLUE, 0.5, 22)}
{gear(872, 96, 8, 27, 20, 9, AMBER, 0.45, 15, reverse=True)}
    <text x="44" y="52" font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="19"
          font-weight="700" fill="url(#fink)" letter-spacing="1.1">
      Build it manually. Understand it deeply. Ship it cleanly.
    </text>
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
    gears = (
        gear(846, 132, 14, 74, 58, 26, BLUE, 0.85, 26)
        + gear(946, 214, 11, 50, 38, 17, AMBER, 0.85, 18, reverse=True)
        + gear(762, 236, 9, 34, 26, 12, DEEP, 0.75, 13)
    )

    ticks = "".join(
        f'<rect x="{60 + i * 26}" y="{H - 26}" width="10" height="2" rx="1" '
        f'fill="{BLUE}" fill-opacity="{0.30 - i * 0.008:.3f}"/>'
        for i in range(30)
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img" aria-label="Isaac Onyango — full-stack developer">
  <title>Isaac Onyango — Full-Stack Developer, Nairobi, Kenya</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#07111f"/>
      <stop offset="46%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#131a24"/>
    </linearGradient>
    <linearGradient id="ink" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="42%" stop-color="{BLUE}"/>
      <stop offset="66%" stop-color="{BLUE}"/>
      <stop offset="100%" stop-color="{AMBER}"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{AMBER}"/>
      <stop offset="100%" stop-color="{DEEP}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BLUE}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{BLUE}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{BLUE}" stop-opacity="0"/>
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

    <rect x="-320" y="0" width="320" height="{H}" fill="url(#beam)">
      <animate attributeName="x" from="-320" to="{W}" dur="7s" repeatCount="indefinite"/>
    </rect>

    <g font-family="Segoe UI,Helvetica,Arial,sans-serif">
      <g opacity="0.9">
        <rect x="60" y="48" width="192" height="26" rx="13" fill="{AMBER}" fill-opacity="0.10"
              stroke="{AMBER}" stroke-opacity="0.45"/>
        <text x="76" y="66" font-size="12" font-weight="600" fill="{AMBER}" letter-spacing="1.8">
          GEARS — SOFTWARE THAT FITS
        </text>
      </g>

      <text x="58" y="146" font-size="56" font-weight="800" fill="url(#ink)" letter-spacing="2">
        ISAAC ONYANGO
      </text>

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
