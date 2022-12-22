#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from collections import defaultdict
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path

from cmk.utils.paths import local_root

from ._parts import get_package_part, PackagePart


def all_local_files() -> Mapping[PackagePart | None, set[Path]]:
    """Return a map of categorized local files

    Remove duplicates caused by symlinks, but keep the symlinks.
    The result of this function may be presented to the user,
    and they are not supposed to see the resolved paths, but the linked ones.
    The linked paths are the ones referenced in the docs,
    while the resolved ones are considered an implementation detail and should be hidden.
    """
    local_files_including_symlinks = {
        Path(root, f)
        for root, _dir, files in os.walk(local_root, followlinks=True)
        for f in files
        if not (f.startswith(".") or f.endswith(("~", ".pyc")))
    }

    resolved_symlinks = {
        resolved for p in local_files_including_symlinks if (resolved := p.resolve()) != p
    }

    categorized_files: dict[PackagePart | None, set[Path]] = defaultdict(set)
    for full_path in sorted(local_files_including_symlinks - resolved_symlinks):
        if (package_part := get_package_part(full_path)) is not None:
            categorized_files[package_part].add(_relative_path(package_part, full_path))
        else:
            # These are rogue files that do not belong to a PackagePart.
            # Worth reporting nevertheless:
            # They *are* being used, and relevant for diagnostics.
            categorized_files[None].add(full_path)
    return categorized_files


def _relative_path(package_part: PackagePart, full_path: Path) -> Path:
    return full_path.resolve().relative_to(package_part.path.resolve())


def all_rule_pack_files() -> set[Path]:
    with suppress(FileNotFoundError):
        return {
            f.relative_to(PackagePart.EC_RULE_PACKS.path)
            for f in PackagePart.EC_RULE_PACKS.path.iterdir()
        }
    return set()
