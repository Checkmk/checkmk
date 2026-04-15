#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Generate per-version changelog files from git log.

Walks the git history of `.ide/vscode/`, parses commits that follow the
conventional commit format documented in CLAUDE.md
(`<type>(vscode): <summary>` on line 1, `v<X.Y.Z>` on line 2,
optional `CMK-<NNN>` on line 3), groups them by version and writes
`.ide/vscode/changelog/v<version>.md`.

Files for old versions are deterministic (immutable history) so re-running the
script produces no diff. The HEAD version's file is rewritten on each run; run
this script after a `git commit --amend` that changes the bump commit.

Usage:
    bazel run //.ide/vscode:generate_changelog
    bazel run //.ide/vscode:generate_changelog -- --since-version 0.1.50
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VSCODE_DIR_REL = ".ide/vscode"

SUBJECT_RE = re.compile(r"^(?P<type>\w+)\(vscode\):\s*(?P<summary>.+)$")
VERSION_RE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)\s*$")
JIRA_RE = re.compile(r"^(CMK-\d+)\s*$")

COMMIT_SEP = "<<<COMMIT>>>"
FIELD_SEP = "<<<FIELD>>>"


def repo_root() -> Path:
    out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    return Path(out)


def parse_version(s: str) -> tuple[int, int, int] | None:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def collect_commits(root: Path) -> dict[str, list[dict[str, str]]]:
    """Return {version: [commits]} sorted by commit order (newest first within a version)."""
    out = subprocess.check_output(
        [
            "git",
            "log",
            f"--format={COMMIT_SEP}%H{FIELD_SEP}%B",
            "--",
            VSCODE_DIR_REL,
        ],
        cwd=root,
        text=True,
    )
    by_version: dict[str, list[dict[str, str]]] = {}
    for chunk in out.split(COMMIT_SEP):
        chunk = chunk.strip()
        if not chunk:
            continue
        sha, _, body = chunk.partition(FIELD_SEP)
        sha = sha.strip()
        lines = body.strip().splitlines()
        if not lines:
            continue
        m = SUBJECT_RE.match(lines[0])
        if not m:
            continue
        version: str | None = None
        jira: str | None = None
        for line in lines[1:]:
            v = VERSION_RE.match(line)
            if v and not version:
                version = v.group("version")
                continue
            j = JIRA_RE.match(line)
            if j and not jira:
                jira = j.group(1)
        if not version:
            continue
        by_version.setdefault(version, []).append(
            {
                "sha": sha,
                "type": m.group("type"),
                "summary": m.group("summary").strip(),
                "jira": jira or "",
            }
        )
    return by_version


def render_changelog(version: str, commits: list[dict[str, str]]) -> str:
    lines = [f"## v{version}", ""]
    for c in commits:
        bullet = f"- **{c['type']}**: {c['summary']}"
        if c["jira"]:
            bullet += f" ({c['jira']})"
        lines.append(bullet)
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--since-version",
        default="0.1.50",
        help="Skip versions older than this (default: 0.1.50).",
    )
    args = ap.parse_args()

    floor = parse_version(args.since_version)
    if floor is None:
        print(f"Invalid --since-version: {args.since_version}", file=sys.stderr)  # noqa: T201
        return 2

    root = repo_root()
    changelog_dir = root / VSCODE_DIR_REL / "changelog"
    changelog_dir.mkdir(exist_ok=True)

    by_version = collect_commits(root)
    written = 0
    skipped_old = 0
    for version, commits in by_version.items():
        ver = parse_version(version)
        if ver is None or ver < floor:
            skipped_old += 1
            continue
        path = changelog_dir / f"v{version}.md"
        new_content = render_changelog(version, commits)
        if path.exists() and path.read_text() == new_content:
            continue
        path.write_text(new_content)
        print(f"Wrote {path.relative_to(root)}")  # noqa: T201
        written += 1
    print(  # noqa: T201
        f"Done. {written} file(s) updated, {skipped_old} version(s) skipped (< v{args.since_version})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
