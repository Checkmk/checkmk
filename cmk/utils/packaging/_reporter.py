#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from contextlib import suppress
from itertools import chain
from pathlib import Path
from stat import filemode
from typing import TypedDict

from cmk.utils.paths import local_root

from ._installed import get_installed_manifests
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


class FileMetaInfo(TypedDict):
    file: str
    package: str
    version: str
    part_id: str
    part_title: str
    mode: str


def files_inventory() -> Sequence[FileMetaInfo]:
    """return an overview of all relevant files found on disk"""
    package_map = {
        (part / file): manifest.id
        for manifest in get_installed_manifests()
        for part, files in manifest.files.items()
        for file in files
    }

    files_and_packages = sorted(
        (
            (part, file, package_map.get((part / file) if part else file))
            for part, files in chain(
                all_local_files().items(),
                ((PackagePart.EC_RULE_PACKS, all_rule_pack_files()),),
            )
            for file in files
        ),
        key=lambda item: ("",) if item[2] is None else (item[2].name, item[2].version.sort_key),
    )
    return [
        FileMetaInfo(
            file=str(file),
            package=package_id.name if package_id else "",
            version=package_id.version if package_id else "",
            part_id=part.ident if part else "",
            part_title=part.ui_title if part else "",
            mode=_get_mode((part.path / file) if part else file),
        )
        for part, file, package_id in files_and_packages
    ]


def _get_mode(path: Path) -> str:
    try:
        return filemode(path.stat().st_mode)
    except OSError as exc:
        return f"<cannot stat: {exc}>"
