# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Edition-specific directory filtering for deployed Python files.

After copying the full ``cmk/`` tree to a site, nonfree edition
directories that do not belong to the target edition must be removed.
The edition hierarchy is encoded as data (not scattered conditionals)
so it can be tested exhaustively.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from cmk.dev_deploy.types import Edition


@dataclass(frozen=True)
class _EditionConfig:
    # Each edition maps to the set of nonfree directory names it KEEPS.
    # The hierarchy is non-linear: cloud includes pro + ultimate but NOT ultimatemt.
    includes: MappingProxyType[Edition, frozenset[str]] = field(
        default_factory=lambda: MappingProxyType(
            {
                Edition.COMMUNITY: frozenset(),
                Edition.PRO: frozenset({"pro"}),
                Edition.ULTIMATE: frozenset({"pro", "ultimate"}),
                Edition.ULTIMATEMT: frozenset({"pro", "ultimate", "ultimatemt"}),
                Edition.CLOUD: frozenset({"pro", "ultimate", "cloud"}),
            }
        )
    )


EDITION_CONFIG = _EditionConfig()

# All nonfree edition directory names that may appear in the deployed tree.
# Note: Does NOT include "cee" -- that is a legacy directory name, not filtered.
ALL_EDITION_DIRS: frozenset[str] = frozenset({"pro", "ultimate", "ultimatemt", "cloud"})

# Editions that include commercial-only features (CMC, DCD, etc.).
# Derived from EDITION_CONFIG so adding a new edition automatically propagates.
PRO_PLUS_EDITIONS: frozenset[str] = frozenset(
    e.value for e in Edition if "pro" in EDITION_CONFIG.includes[e]
)


def editions_to_remove(site_edition: Edition) -> frozenset[str]:
    """Return the set of edition directory names that should be removed.

    Pure function with no side effects.

    Args:
        site_edition: The edition of the target OMD site.

    Returns:
        A frozenset of directory names (e.g. ``{"ultimatemt", "cloud"}``)
        that do not belong to the given edition and should be deleted.
    """
    return ALL_EDITION_DIRS - EDITION_CONFIG.includes[site_edition]


def filter_edition_files(files: list[str], site_edition: Edition) -> list[str]:
    """Filter out individual file paths belonging to excluded editions.

    Unlike :func:`filter_editions` which walks a directory tree,
    this function operates on a flat list of file paths (e.g. ``cmk/gui/nonfree/cloud/dashboard.py``)
    and checks whether any path component matches an excluded edition directory name.

    This is a pure function with no filesystem access.

    Args:
        files: List of file paths relative to the repo root.
        site_edition: The edition of the target OMD site.

    Returns:
        Files that should be deployed (not belonging to excluded editions).
    """
    excluded = editions_to_remove(site_edition)
    if not excluded:
        return files

    result: list[str] = []
    for filepath in files:
        parts = filepath.split("/")
        if not any(part in excluded for part in parts):
            result.append(filepath)
    return result


def filter_editions(deploy_root: Path, site_edition: Edition) -> list[Path]:
    """Remove edition-specific directories that don't belong to the target edition.

    Walks the deployed file tree and removes any directories whose name matches
    an edition that is NOT included in the target edition's hierarchy.  Modifies
    ``dirnames`` in-place during :func:`os.walk` to prevent descending into
    removed subtrees.

    This matches the behaviour of ``cmk/.f12`` lines 50-65.

    Args:
        deploy_root: Root of the deployed Python tree
            (e.g. ``<site>/lib/python3/cmk``).
        site_edition: The edition of the target OMD site.

    Returns:
        List of absolute paths that were removed.
    """
    to_remove = editions_to_remove(site_edition)
    if not to_remove:
        return []

    removed: list[Path] = []
    for dirpath, dirnames, _ in os.walk(deploy_root):
        # Copy the list since we modify it in-place
        for dirname in dirnames[:]:
            if dirname in to_remove:
                full_path = Path(dirpath) / dirname
                shutil.rmtree(full_path)
                dirnames.remove(dirname)
                removed.append(full_path)

    return removed
