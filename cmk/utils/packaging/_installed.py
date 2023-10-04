#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from ._mkp import Manifest, PackagePart, read_manifest_optionally
from ._type_defs import PackageID, PackageName


class Installer:
    def __init__(self, manifests_dir: Path) -> None:
        self._manifests_dir: Final = manifests_dir

    def _path_for(self, name: PackageName) -> Path:
        return self._manifests_dir / str(name)

    def _installed_names(
        self,
    ) -> Sequence[PackageName]:
        return sorted(PackageName(p.name) for p in self._manifests_dir.iterdir())

    def get_installed_manifest(self, package_name: PackageName) -> Manifest | None:
        if not self.is_installed(package_name):
            # LBYL prevents an error being logged if the package is not installed
            return None
        return read_manifest_optionally(self._path_for(package_name))

    def get_installed_manifests(self) -> Sequence[Manifest]:
        return [
            manifest
            for name in self._installed_names()
            if (manifest := self.get_installed_manifest(name)) is not None
        ]

    def get_packaged_files(
        self,
    ) -> Mapping[PackagePart, Mapping[Path, PackageID]]:
        packaged_files: dict[PackagePart, dict[Path, PackageID]] = {p: {} for p in PackagePart}
        for manifest in self.get_installed_manifests():
            for part in PackagePart:
                packaged_files[part].update(
                    (path, manifest.id) for path in manifest.files.get(part, ())
                )
        return packaged_files

    def is_installed(self, name: PackageName) -> bool:
        return self._path_for(name).exists()

    def add_installed_manifest(self, manifest: Manifest) -> None:
        self._path_for(manifest.name).write_text(manifest.file_content())

    def remove_installed_manifest(self, name: PackageName) -> None:
        self._path_for(name).unlink(missing_ok=True)
