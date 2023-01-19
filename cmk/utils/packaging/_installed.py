#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

import cmk.utils.paths

from ._mkp import Manifest, read_manifest_optionally
from ._parts import PackagePart
from ._type_defs import PackageName

PACKAGES_DIR: Final = cmk.utils.paths.omd_root / "var/check_mk/packages"


def _path_for(name: PackageName) -> Path:
    return PACKAGES_DIR / str(name)


def _installed_names() -> Sequence[PackageName]:
    return sorted(PackageName(p.name) for p in PACKAGES_DIR.iterdir())


def get_installed_manifest(
    package_name: PackageName, log: logging.Logger | None = None
) -> Manifest | None:
    return read_manifest_optionally(_path_for(package_name), log)


def get_installed_manifests(log: logging.Logger | None = None) -> Sequence[Manifest]:
    return [
        manifest
        for name in _installed_names()
        if (manifest := get_installed_manifest(name, log)) is not None
    ]


def get_packaged_files() -> Mapping[PackagePart, set[Path]]:
    packaged_files: dict[PackagePart, set[Path]] = {p: set() for p in PackagePart}
    for manifest in get_installed_manifests():
        for part in PackagePart:
            packaged_files[part].update(manifest.files.get(part, ()))
    return packaged_files


def is_installed(name: PackageName) -> bool:
    return _path_for(name).exists()


def add_installed_manifest(manifest: Manifest) -> None:
    _path_for(manifest.name).write_text(manifest.file_content())


def remove_installed_manifest(name: PackageName) -> None:
    _path_for(name).unlink(missing_ok=True)
