#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from typing import Final

import cmk.utils.paths

from ._manifest import Manifest, read_manifest_optionally
from ._parts import PackagePart
from ._type_defs import PackageName

PACKAGES_DIR: Final = cmk.utils.paths.omd_root / "var/check_mk/packages"


def _installed_names() -> Sequence[PackageName]:
    return sorted(PackageName(p.name) for p in PACKAGES_DIR.iterdir())


def get_installed_manifest(
    package_name: PackageName, log: logging.Logger | None = None
) -> Manifest | None:
    return read_manifest_optionally(PACKAGES_DIR / str(package_name), log)


def get_installed_manifests(log: logging.Logger | None = None) -> Sequence[Manifest]:
    return [
        manifest
        for name in _installed_names()
        if (manifest := get_installed_manifest(name, log)) is not None
    ]


def get_packaged_files() -> Mapping[PackagePart, set[str]]:
    packaged_files: dict[PackagePart, set[str]] = {p: set() for p in PackagePart}
    for manifest in get_installed_manifests():
        for part in PackagePart:
            packaged_files[part].update(manifest.files.get(part.ident, ()))
    return packaged_files


def is_installed(name: PackageName) -> bool:
    return (PACKAGES_DIR / str(name)).exists()


def add_installed_manifest(manifest: Manifest) -> None:
    (PACKAGES_DIR / str(manifest.name)).write_text(manifest.file_content())


def remove_installed_manifest(name: PackageName) -> None:
    (PACKAGES_DIR / str(name)).unlink(missing_ok=True)
