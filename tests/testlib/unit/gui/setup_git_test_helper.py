#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers for asserting that an endpoint does not commit the Setup GIT repo."""

import subprocess
from pathlib import Path


def init_setup_git_repo(config_dir: Path) -> None:
    """Initialize a Setup GIT repo, then rewrite a tracked file to leave the tree dirty."""
    tracked = config_dir / "multisite.d" / "wato" / "global.mk"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("# committed\n")

    def _git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=config_dir, check=True, capture_output=True)

    _git("init", "-q")
    _git("config", "user.email", "check_mk")
    _git("config", "user.name", "check_mk")
    _git("add", "-A")
    _git("commit", "-q", "-m", "Initialized GIT for Checkmk")
    tracked.write_text("# rewritten by cmk-update-config\n")


def setup_git_commit_subjects(config_dir: Path) -> list[str]:
    """Return the subjects of the commits in the Setup GIT repo, newest first."""
    return subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=config_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
