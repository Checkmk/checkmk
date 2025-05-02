#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from collections.abc import Mapping, Sequence
from contextlib import suppress
from itertools import chain
from pathlib import Path
from stat import filemode
from typing import TypedDict

from ._mkp import PackagePart
from ._parts import PathConfig, ui_title
from ._type_defs import PackageID


def _all_local_files(path_config: PathConfig) -> Mapping[PackagePart | None, set[Path]]:
    """Return a map of categorized local files

    TODO: this is outdated, fix it.
    Remove duplicates caused by symlinks, but keep the symlinks.
    The result of this function may be presented to the user,
    and they are not supposed to see the resolved paths, but the linked ones.
    The linked paths are the ones referenced in the docs,
    while the resolved ones are considered an implementation detail and should be hidden.
    """
    local_files_including_symlinks = {
        Path(root, f)
        for root, _dir, files in os.walk(path_config.local_root, followlinks=True)
        for f in files
        if not (f.startswith(".") or f.endswith(("~", ".pyc")))
    }

    resolved_to_abstracted: dict[Path, Path] = {}
    for path in local_files_including_symlinks:
        resolved = path.resolve()
        if resolved not in resolved_to_abstracted or resolved_to_abstracted[resolved] == resolved:
            resolved_to_abstracted[resolved] = path

    return categorize_files(resolved_to_abstracted, path_config)


def categorize_files(
    resolved_to_abstracted: Mapping[Path, Path], path_config: PathConfig
) -> Mapping[PackagePart | None, set[Path]]:
    categorized_files: dict[PackagePart | None, set[Path]] = {}
    for resolved_full_path, user_full_path in resolved_to_abstracted.items():
        if (package_part := path_config.get_part(resolved_full_path)) is not None:
            categorized_files.setdefault(package_part, set()).add(
                _relative_path(package_part, resolved_full_path, path_config)
            )
        else:
            # These are rogue files that do not belong to a PackagePart.
            # Worth reporting nevertheless:
            # They *are* being used, and relevant for diagnostics.
            categorized_files.setdefault(None, set()).add(user_full_path)
    return categorized_files


def _relative_path(
    package_part: PackagePart, resolved_full_path: Path, path_config: PathConfig
) -> Path:
    rpath = resolved_full_path.relative_to(path_config.resolved_paths[package_part])
    return rpath


def all_rule_pack_files(ec_path: Path) -> set[Path]:
    with suppress(FileNotFoundError):
        return {f.relative_to(ec_path) for f in ec_path.iterdir()}
    return set()


def all_packable_files(path_config: PathConfig) -> Mapping[PackagePart, set[Path]]:
    """Collect all files that can be in a package in principle

    Incudes already packaged files and EC exported rule packs.
    Excludes rogue files (not belonging to a package part).
    """
    return {
        **{p: f for p, f in _all_local_files(path_config).items() if p is not None},
        PackagePart.EC_RULE_PACKS: all_rule_pack_files(
            path_config.get_path(PackagePart.EC_RULE_PACKS)
        ),
    }


class FileMetaInfo(TypedDict):
    file: str
    package: str
    version: str
    part_id: str
    part_title: str
    mode: str


def files_inventory(
    package_map: Mapping[PackagePart, Mapping[Path, PackageID]], path_config: PathConfig
) -> Sequence[FileMetaInfo]:
    """return an overview of all relevant files found on disk"""
    files_and_packages = sorted(
        (
            (part, file, package_map[part].get(file) if part else None)
            for part, files in chain(
                _all_local_files(path_config).items(),
                (
                    (
                        PackagePart.EC_RULE_PACKS,
                        all_rule_pack_files(path_config.get_path(PackagePart.EC_RULE_PACKS)),
                    ),
                ),
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
            part_title=ui_title(part, lambda s: s) if part else "",
            mode=_get_mode((path_config.get_path(part) / file) if part else file),
        )
        for part, file, package_id in files_and_packages
    ]


def _get_mode(path: Path) -> str:
    try:
        return filemode(path.stat().st_mode)
    except OSError as exc:
        return f"<cannot stat: {exc}>"
