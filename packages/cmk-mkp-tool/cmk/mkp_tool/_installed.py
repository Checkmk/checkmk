#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from ._mkp import Manifest, PackagePart, read_manifest_optionally
from ._type_defs import PackageID, PackageName

_REPLACED_LIB_CHECK_MK_LINK_NAME = "check_mk"
_REPLACED_LIB_CHECK_MK_LINK_DESTINATION = "python3/cmk"


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
        self._path_for(manifest.name).write_text(
            replace_legacy_linked_lib_check_mk_path(manifest).file_content()
        )

    def remove_installed_manifest(self, name: PackageName) -> None:
        self._path_for(name).unlink(missing_ok=True)


def replace_legacy_linked_lib_check_mk_path(manifest: Manifest) -> Manifest:
    """Replace the legacy linked lib check_mk path with the new one.

    We used to have a link lib/check_mk, pointing to lib/python3/cmk.
    We since removed that link, but old manifests may still reference it.
    This function replaces the legacy path with the new one, so that we
    correctly identify the affected files as belonging to this package.
    """
    if not (legacy_refs := _extract_legacy_files(manifest)):
        return manifest
    return Manifest(
        title=manifest.title,
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        version_packaged=manifest.version_packaged,
        version_min_required=manifest.version_min_required,
        version_usable_until=manifest.version_usable_until,
        author=manifest.author,
        download_url=manifest.download_url,
        files={
            **manifest.files,
            PackagePart.LIB: [
                _make_new_path(p) if p in legacy_refs else p
                for p in manifest.files[PackagePart.LIB]
            ],
        },
    )


def cleanup_legacy_linked_lib_check_mk_path(lib_path: Path, legacy_manifest: Manifest) -> None:
    """Move unpacked legacy files to new location.

    We used to have a link lib/check_mk, pointing to lib/python3/cmk.
    We since removed that link, but old manifests may still reference it.
    """
    for file in _extract_legacy_files(legacy_manifest):
        src = lib_path / file
        dst = lib_path / _make_new_path(file)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        for _length in range(len(file.parts) - 1):
            src = src.parent
            try:
                src.rmdir()
            except OSError:
                break


def _extract_legacy_files(manifest: Manifest) -> Sequence[Path]:
    return [
        p
        for p in manifest.files.get(PackagePart.LIB, ())
        if p.parts[0] == _REPLACED_LIB_CHECK_MK_LINK_NAME
    ]


def _make_new_path(old_path: Path) -> Path:
    return Path(_REPLACED_LIB_CHECK_MK_LINK_DESTINATION, *old_path.parts[1:])
