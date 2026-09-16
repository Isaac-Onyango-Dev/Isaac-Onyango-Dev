"""Run with: python scripts/test_build_profile.py"""

import tempfile
from pathlib import Path

from build_profile import activity_feed, patch_readme


def ev(kind, repo, when, **payload):
    return {"type": kind, "repo": {"name": f"me/{repo}"}, "created_at": when, "payload": payload}


events = [
    ev("PushEvent", "app", "2026-09-10T10:00:00Z"),
    ev("PushEvent", "app", "2026-09-12T10:00:00Z"),          # same repo+verb: collapsed
    ev("PushEvent", "me", "2026-09-13T10:00:00Z"),           # profile repo: hidden
    ev("CreateEvent", "app", "2026-09-11T10:00:00Z", ref_type="branch"),  # branches: hidden
    ev("CreateEvent", "tool", "2026-09-09T10:00:00Z", ref_type="repository"),
    ev("IssuesEvent", "tool", "2026-09-08T10:00:00Z", action="closed"),   # only opened
    ev("WatchEvent", "tool", "2026-09-14T10:00:00Z"),        # unknown type: hidden
]
lines = activity_feed("me", events).splitlines()
assert lines == [
    "- `12 Sep` &nbsp; Pushed to **[app](https://github.com/me/app)**",
    "- `09 Sep` &nbsp; Created **[tool](https://github.com/me/tool)**",
], lines
assert activity_feed("me", []).startswith("- Nothing")

with tempfile.TemporaryDirectory() as tmp:
    readme = Path(tmp) / "README.md"
    readme.write_text("a <!-- X:START -->old<!-- X:END --> b", encoding="utf-8")
    for _ in range(2):  # rerunning must not stack content
        patch_readme(readme, {"X": r"new \1", "MISSING": "ignored"})
    assert readme.read_text(encoding="utf-8") == r"a <!-- X:START -->new \1<!-- X:END --> b"

print("ok")
