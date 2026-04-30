#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers that read repo-level metadata (defines.make, etc.)."""

from __future__ import annotations

import re
from pathlib import Path

_BRANCH_VERSION_RE = re.compile(r"^BRANCH_VERSION\s*:?=\s*(\S+)", re.MULTILINE)


def read_branch_version(repo: Path) -> str:
    """Return the ``BRANCH_VERSION`` value from ``<repo>/defines.make``.

    This is the canonical "what release does this commit target?" label set
    per branch in checkmk's release process (e.g. ``2.6.0`` on master).
    Preferred over ``git rev-parse --abbrev-ref HEAD`` for the row's
    ``branch`` column, since topic branches inherit the version of their
    base branch.
    """
    text = (repo / "defines.make").read_text(encoding="utf-8")
    match = _BRANCH_VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"BRANCH_VERSION not found in {repo}/defines.make")
    return match.group(1)
