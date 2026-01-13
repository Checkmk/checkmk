#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import shutil
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path


def snapshot_local_dir(local_root: Path, config_path: Path) -> None:
    """Create a snapshot of the local directory into the new config path.

    At the time of writing this is only written to be used by the relay, but it would
    also be correct for the core(s) to use it.
    """
    source_path = local_root.resolve()  # avoid trouble with /omd vs /opt/omd
    target_path = (config_path / "local").resolve()
    hash_path = Path(f"{target_path}.hash")
    try:
        link_handler = _DereferenceExternalLinks(source_path, target_path)
        shutil.copytree(
            source_path,
            target_path,
            symlinks=True,
            ignore=link_handler.collect,
        )
        link_handler.copy_encountered_external_links()
        hash_value = _hash_local_dir(target_path)
    except FileNotFoundError:
        hash_value = ""
    hash_path.write_text(hash_value)


class _DereferenceExternalLinks:
    """We dereference symlinks that point outside of the local dir being snapshotted.

    This is required for the relay, but it also is in line with the general idea of making
    a self-contained snapshot.
    """

    def __init__(self, base_path: Path, target_path: Path) -> None:
        self.base_path = base_path
        self.target_path = target_path
        self._external_links = list[tuple[Path, Path]]()

    def collect(self, dir: str, names: Sequence[str]) -> Iterable[str]:
        external_links = self._filter_external_links(dir, names)
        self._external_links.extend(external_links.values())
        return external_links

    def _filter_external_links(
        self, current_dir: str, names: Sequence[str]
    ) -> Mapping[str, tuple[Path, Path]]:
        return {
            name: (link_dst, path)
            for name in names
            if (link_dst := self._external_link(path := Path(current_dir) / name)) is not None
        }

    def _external_link(self, path: Path) -> Path | None:
        if not path.is_symlink():
            return None
        link_path = path.readlink()
        link_dst = path.resolve()
        # Dangling links can not be dereferenced
        if not link_dst.exists():
            return None
        # absolute links always point outside after copy.
        if link_path.is_absolute():
            return link_dst
        # relative but pointing outside
        if not link_dst.is_relative_to(self.base_path):
            return link_dst
        return None

    def copy_encountered_external_links(self) -> None:
        for src, dst in self._external_links:
            try:
                shutil.copy2(src, self.target_path / dst.relative_to(self.base_path))
            except FileNotFoundError:
                pass  # race condition


def _hash_local_dir(path: Path) -> str:
    """create a hash of a directory tree based on file paths and contents"""
    hasher = hashlib.blake2b()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            hasher.update(file_path.relative_to(path).as_posix().encode())
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
