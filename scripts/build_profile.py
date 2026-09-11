#!/usr/bin/env python3
"""
Self-hosted GitHub profile generator.

Builds every stat card as a local SVG and rewrites the repository showcase
inside README.md. Nothing on the profile depends on a third-party image
service, so nothing can silently break when one of them goes down.

Outputs:
    assets/stats.svg        engineering metrics card
    assets/languages.svg    language distribution card
    assets/activity.svg     contribution heatmap for the last year
    README.md               repository showcase between the REPOS markers

Usage:
    python scripts/build_profile.py [--user LOGIN] [--root PATH]

A GITHUB_TOKEN in the environment is optional; it only raises the API rate
limit. Everything the script needs is public.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

API = "https://api.github.com"
UA = "profile-builder"

# ── palette ────────────────────────────────────────────────────────────────
BG = "#0d1117"
CARD = "#0f141b"
EDGE = "#1f2a37"
TEXT = "#c9d1d9"
MUTED = "#7d8590"
BLUE = "#58a6ff"
DEEP = "#1f6feb"
AMBER = "#f0883e"
GREEN = "#3fb950"
VIOLET = "#a371f7"

LANG_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572a5",
    "SCSS": "#c6538c",
    "CSS": "#663399",
    "HTML": "#e34c26",
    "Shell": "#89e051",
    "Dart": "#00b4ab",
    "Java": "#b07219",
    "Kotlin": "#a97bff",
    "PHP": "#4f5d95",
    "C#": "#178600",
    "C++": "#f34b7d",
    "Dockerfile": "#384d54",
    "Batchfile": "#c1f12e",
    "Inno Setup": "#264b99",
    "PowerShell": "#012456",
    "Makefile": "#427819",
    "Rust": "#dea584",
    "Go": "#00add8",
}
FALLBACK_COLORS = [BLUE, AMBER, GREEN, VIOLET, "#e3b341", "#db6d28", "#2ea043"]

HEAT = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


# ── data access ────────────────────────────────────────────────────────────
def request(url: str, html: bool = False):
    headers = {"User-Agent": UA}
    if html:
        headers["Accept"] = "text/html"
    else:
        headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and not html:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8", "replace")
    if html:
        return raw
    # An empty repository answers 204 with no body.
    return json.loads(raw) if raw.strip() else []


def fetch_profile(user: str) -> dict:
    return request(f"{API}/users/{user}")


def fetch_repos(user: str) -> list[dict]:
    out, page = [], 1
    while True:
        batch = request(f"{API}/users/{user}/repos?per_page=100&page={page}&sort=pushed")
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in out if not r["fork"] and not r["archived"]]


def fetch_languages(repos: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        try:
            for lang, size in request(repo["languages_url"]).items():
                totals[lang] = totals.get(lang, 0) + size
        except urllib.error.HTTPError:
            continue
    return totals


def fetch_commits(user: str, repos: list[dict]) -> int:
    total = 0
    for repo in repos:
        try:
            contributors = request(f"{API}/repos/{repo['full_name']}/contributors?per_page=100")
        except urllib.error.HTTPError:
            continue
        if not isinstance(contributors, list):
            continue
        for entry in contributors:
            if (entry.get("login") or "").lower() == user.lower():
                total += entry.get("contributions", 0)
    return total


def fetch_contributions(user: str) -> list[tuple[date, int]]:
    """Parse the public contribution calendar straight from github.com."""
    try:
        page = request(f"https://github.com/users/{user}/contributions", html=True)
    except Exception:
        return []
    cells = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d+)"', page)
    labels = re.findall(r">\s*(No|[\d,]+)\s+contributions? on", page)
    days: list[tuple[date, int]] = []
    for index, (iso, level) in enumerate(cells):
        count = 0
        if index < len(labels):
            raw = labels[index]
            count = 0 if raw == "No" else int(raw.replace(",", ""))
        elif level != "0":
            count = int(level)
        days.append((date.fromisoformat(iso), count))
    days.sort(key=lambda item: item[0])
    return days


# ── svg helpers ────────────────────────────────────────────────────────────
def svg_open(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        "<defs>",
        f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{DEEP}" stop-opacity="0.55"/>'
        f'<stop offset="55%" stop-color="{EDGE}" stop-opacity="0.9"/>'
        f'<stop offset="100%" stop-color="{AMBER}" stop-opacity="0.35"/></linearGradient>',
        '<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#16202c"/><stop offset="100%" stop-color="{CARD}"/>'
        "</linearGradient>",
        f'<pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<path d="M22 0H0V22" fill="none" stroke="{BLUE}" stroke-opacity="0.05" stroke-width="1"/>'
        "</pattern>",
        "</defs>",
        f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="14" '
        f'fill="url(#sheen)" stroke="url(#edge)" stroke-width="1.5"/>',
        f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="13" fill="url(#grid)"/>',
    ]


def card_heading(parts: list[str], label: str, sub: str, width: int) -> None:
    parts.append(
        f'<text x="22" y="34" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="15" font-weight="700" fill="{TEXT}" letter-spacing="1.6">{escape(label)}</text>'
    )
    parts.append(
        f'<text x="{width - 22}" y="34" text-anchor="end" '
        f'font-family="Consolas,monospace" font-size="11" fill="{MUTED}">{escape(sub)}</text>'
    )
    parts.append(f'<rect x="22" y="44" width="34" height="2.5" rx="1.25" fill="{AMBER}"/>')
    parts.append(
        f'<rect x="60" y="44" width="{width - 82}" height="2.5" rx="1.25" '
        f'fill="{BLUE}" fill-opacity="0.18"/>'
    )


def write(path: Path, parts: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n</svg>\n", encoding="utf-8")
    print(f"  wrote {path.name}")


# ── cards ──────────────────────────────────────────────────────────────────
def build_stats_card(path: Path, profile: dict, repos: list[dict], commits: int,
                     year_contributions: int, streak: int, languages: int) -> None:
    width, height = 500, 246
    parts = svg_open(width, height, "GitHub statistics")
    card_heading(parts, "ENGINEERING METRICS", datetime.now(timezone.utc).strftime("%d %b %Y"), width)

    stars = sum(r["stargazers_count"] for r in repos)
    tiles = [
        ("Public repositories", f"{profile['public_repos']}", BLUE),
        ("Total commits", f"{commits:,}", AMBER),
        ("Contributions / year", f"{year_contributions:,}", GREEN),
        ("Longest streak", f"{streak} days", VIOLET),
        ("Stars earned", f"{stars}", "#e3b341"),
        ("Languages shipped", f"{languages}", BLUE),
    ]
    col_w = (width - 44) / 2
    for index, (label, value, colour) in enumerate(tiles):
        x = 22 + (index % 2) * col_w
        y = 74 + (index // 2) * 56
        parts.append(f'<rect x="{x}" y="{y}" width="3" height="34" rx="1.5" fill="{colour}"/>')
        parts.append(
            f'<text x="{x + 14}" y="{y + 15}" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="10.5" fill="{MUTED}" letter-spacing="0.8">{escape(label.upper())}</text>'
        )
        parts.append(
            f'<text x="{x + 14}" y="{y + 33}" font-family="Consolas,monospace" '
            f'font-size="19" font-weight="700" fill="{TEXT}">{escape(value)}</text>'
        )
    write(path, parts)


def build_language_card(path: Path, totals: dict[str, int]) -> None:
    width, height = 500, 246
    parts = svg_open(width, height, "Language distribution")
    grand = sum(totals.values()) or 1
    ordered = sorted(totals.items(), key=lambda item: -item[1])
    top = ordered[:7]
    rest = sum(size for _, size in ordered[7:])
    if rest:
        top.append(("Other", rest))
    card_heading(parts, "LANGUAGE DISTRIBUTION", f"{grand / 1_000_000:.2f} M bytes", width)

    bar_x, bar_y, bar_w = 22.0, 64.0, float(width - 44)
    parts.append(
        f'<clipPath id="barclip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" '
        f'height="13" rx="6.5"/></clipPath>'
    )
    cursor = bar_x
    for index, (lang, size) in enumerate(top):
        span = bar_w * size / grand
        colour = LANG_COLORS.get(lang, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
        parts.append(
            f'<rect x="{cursor:.2f}" y="{bar_y}" width="{span + 0.6:.2f}" height="13" '
            f'fill="{colour}" clip-path="url(#barclip)"/>'
        )
        cursor += span

    col_w = (width - 44) / 2
    for index, (lang, size) in enumerate(top):
        share = size / grand * 100
        colour = LANG_COLORS.get(lang, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
        x = 22 + (index % 2) * col_w
        y = 112 + (index // 2) * 30
        parts.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{colour}"/>')
        parts.append(
            f'<text x="{x + 17}" y="{y}" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="12" fill="{TEXT}">{escape(lang)}</text>'
        )
        parts.append(
            f'<text x="{x + col_w - 16}" y="{y}" text-anchor="end" '
            f'font-family="Consolas,monospace" font-size="11.5" fill="{MUTED}">{share:.1f}%</text>'
        )
    write(path, parts)


def build_activity_card(path: Path, days: list[tuple[date, int]]) -> None:
    width, height = 1012, 232
    parts = svg_open(width, height, "Contribution activity")
    total = sum(count for _, count in days)
    card_heading(parts, "CONTRIBUTION ACTIVITY", f"{total:,} contributions in the last year", width)

    if not days:
        parts.append(
            f'<text x="22" y="110" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="12" fill="{MUTED}">Calendar unavailable.</text>'
        )
        write(path, parts)
        return

    cell, gap = 15, 3
    origin_x, origin_y = 40, 74
    first = days[0][0]
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    levels = {0: 0, 1: 1, 2: 2, 3: 3}
    month_seen: set[str] = set()

    for day, count in days:
        offset = (day - start).days
        week, weekday = divmod(offset, 7)
        if count == 0:
            level = 0
        elif count <= 2:
            level = 1
        elif count <= 5:
            level = 2
        elif count <= 9:
            level = 3
        else:
            level = 4
        level = levels.get(level, level)
        x = origin_x + week * (cell + gap)
        y = origin_y + weekday * (cell + gap)
        opacity = "1" if level else "0.85"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{HEAT[level]}" fill-opacity="{opacity}">'
            f"<title>{day.isoformat()}: {count} contributions</title></rect>"
        )
        tag = day.strftime("%b")
        if day.day <= 7 and tag not in month_seen and weekday == 0:
            month_seen.add(tag)
            parts.append(
                f'<text x="{x}" y="{origin_y - 8}" font-family="Segoe UI,Helvetica,Arial,sans-serif" '
                f'font-size="10" fill="{MUTED}">{tag}</text>'
            )

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(
            f'<text x="10" y="{origin_y + row * (cell + gap) + 11}" '
            f'font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="9.5" '
            f'fill="{MUTED}">{label}</text>'
        )

    legend_x = width - 152
    legend_y = height - 19
    parts.append(
        f'<text x="{legend_x - 8}" y="{legend_y + 9}" text-anchor="end" '
        f'font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="{MUTED}">Less</text>'
    )
    for index, colour in enumerate(HEAT):
        parts.append(
            f'<rect x="{legend_x + index * 16}" y="{legend_y}" width="12" height="12" '
            f'rx="3" fill="{colour}"/>'
        )
    parts.append(
        f'<text x="{legend_x + len(HEAT) * 16 + 6}" y="{legend_y + 9}" '
        f'font-family="Segoe UI,Helvetica,Arial,sans-serif" font-size="10" fill="{MUTED}">More</text>'
    )
    write(path, parts)


# ── readme showcase ────────────────────────────────────────────────────────
BADGE = "https://img.shields.io/badge"

TECH_HINTS = {
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "Python": "3776AB",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "Dart": "0175C2",
}


def longest_streak(days: list[tuple[date, int]]) -> int:
    best = run = 0
    for _, count in days:
        run = run + 1 if count else 0
        best = max(best, run)
    return best


def repo_showcase(user: str, repos: list[dict]) -> str:
    visible = [r for r in repos if r["name"].lower() != user.lower()]
    visible.sort(key=lambda r: (r["stargazers_count"], r["pushed_at"]), reverse=True)

    lines = ["<table>", "<tr>"]
    for index, repo in enumerate(visible):
        if index and index % 2 == 0:
            lines += ["</tr>", "<tr>"]
        name = repo["name"]
        desc = (repo["description"] or "No description yet.").strip()
        if len(desc) > 118:
            desc = desc[:115].rsplit(" ", 1)[0] + "…"
        lang = repo["language"] or "Mixed"
        colour = TECH_HINTS.get(lang, "6E7681")
        stars = repo["stargazers_count"]
        meta = f"`{lang}`"
        if stars:
            meta += f" &nbsp;·&nbsp; ★ {stars}"
        if repo["topics"]:
            meta += " &nbsp;·&nbsp; " + " ".join(f"`{t}`" for t in repo["topics"][:3])
        home = repo["homepage"] or ""
        buttons = (
            f'<a href="{repo["html_url"]}">'
            f'<img src="{BADGE}/Source-0D1117?style=flat-square&logo=github&logoColor=white" alt="Source"/></a>'
        )
        if home:
            buttons += (
                f' <a href="{home}">'
                f'<img src="{BADGE}/Live%20Demo-{colour}?style=flat-square&logo=googlechrome&logoColor=white" alt="Live demo"/></a>'
            )
        lines += [
            "<td width=\"50%\" valign=\"top\">",
            "",
            f"#### [{name}]({repo['html_url']})",
            "",
            f"{desc}",
            "",
            f"{meta}",
            "",
            f"{buttons}",
            "",
            "</td>",
        ]
    if len(visible) % 2:
        lines.append('<td width="50%"></td>')
    lines += ["</tr>", "</table>"]
    return "\n".join(lines)


def patch_readme(readme: Path, block: str) -> None:
    text = readme.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(<!-- REPOS:START -->)(.*?)(<!-- REPOS:END -->)", re.DOTALL
    )
    if not pattern.search(text):
        print("  README markers missing; showcase not updated", file=sys.stderr)
        return
    readme.write_text(
        pattern.sub(lambda m: f"{m.group(1)}\n{block}\n{m.group(3)}", text),
        encoding="utf-8",
    )
    print("  wrote README.md showcase")


# ── entry point ────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default=os.environ.get("PROFILE_USER", "Isaac-Onyango-Dev"))
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--cache",
        help="reuse API results from this JSON file, writing it on the first run; "
             "useful while tweaking the card layouts without spending rate limit",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    assets = root / "assets"
    user = args.user
    cache = Path(args.cache) if args.cache else None

    print(f"building profile for {user}")
    if cache and cache.exists():
        print(f"  reading cached API data from {cache}")
        snapshot = json.loads(cache.read_text(encoding="utf-8"))
        profile, repos = snapshot["profile"], snapshot["repos"]
        languages, commits = snapshot["languages"], snapshot["commits"]
    else:
        profile = fetch_profile(user)
        repos = fetch_repos(user)
        languages = fetch_languages(repos)
        commits = fetch_commits(user, repos)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(
                json.dumps(
                    {"profile": profile, "repos": repos,
                     "languages": languages, "commits": commits},
                    indent=1,
                ),
                encoding="utf-8",
            )
    days = fetch_contributions(user)
    year_total = sum(count for _, count in days)

    build_stats_card(
        assets / "stats.svg", profile, repos, commits, year_total,
        longest_streak(days), len(languages),
    )
    build_language_card(assets / "languages.svg", languages)
    build_activity_card(assets / "activity.svg", days)
    patch_readme(root / "README.md", repo_showcase(user, repos))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
