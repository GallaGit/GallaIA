#!/usr/bin/env python3
"""Smoke-check that relative markdown links resolve to existing files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "ftp://")


def iter_markdown() -> list[Path]:
    files = [ROOT / "README.md"]
    files.extend(sorted(ROOT.joinpath("docs").rglob("*.md")))
    for extra in ("backend/README.md", "frontend/README.md"):
        p = ROOT / extra
        if p.is_file():
            files.append(p)
    return files


def normalize_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith("#") or target.startswith("<"):
        return None
    if any(target.lower().startswith(p) for p in SKIP_PREFIXES):
        return None
    if "://" in target:
        return None
    if target.startswith("mailto:"):
        return None
    # Drop optional title: path "title"
    if target.startswith('"') or target.startswith("'"):
        return None
    target = target.split()[0].strip("<>")
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    if not target:
        return None
    return target


def main() -> int:
    missing: list[str] = []
    checked = 0
    for md in iter_markdown():
        text = md.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = normalize_target(match.group(1))
            if target is None:
                continue
            checked += 1
            dest = (md.parent / target).resolve()
            try:
                dest.relative_to(ROOT)
            except ValueError:
                # Allow links that escape the repo only if the file exists
                # (should not happen for docs).
                pass
            if not dest.exists():
                rel_md = md.relative_to(ROOT)
                missing.append(f"{rel_md}: {target}")
    if missing:
        print(f"Missing {len(missing)} of {checked} relative markdown links:")
        for item in missing:
            print(f"  - {item}")
        return 1
    print(f"OK: {checked} relative markdown links resolve ({len(iter_markdown())} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
