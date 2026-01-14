#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fetcher config path manipulation."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.ccc.store import DimSerializer, ObjectStore

__all__ = ["VersionedConfigPath", "ConfigCreationContext"]


@dataclass(frozen=True)
class ConfigCreationContext:
    """Hold information on the currently active config and the one being created."""

    path_active: Path
    path_created: Path
    serial_created: int


def detect_latest_config_path(base: Path) -> Path:
    """Resolve the 'latest' symlink to the latest config path.

    Using this probably subject to a race condition, as the
    CMC might choose to remove that config.
    """
    latest_link_path = VersionedConfigPath.make_latest_path(base)
    return latest_link_path.resolve()


class VersionedConfigPath:
    @classmethod
    def make_root_path(cls, base: Path) -> Path:
        # Note - Security: This must remain hard-coded to a path not writable by others.
        #                  See BNS:c3c5e9.
        return base / "var/check_mk/core/helper_config"

    @classmethod
    def make_latest_path(cls, base: Path) -> Path:
        return cls.make_root_path(base).joinpath("latest")

    def __init__(self, base: Path, serial: int) -> None:
        super().__init__()
        self.base: Final = base
        self.root: Final = self.make_root_path(base)
        # TODO: The fact that this can be interpreted as an int
        # is an implementation detail of _increment_to_next_serial.
        # But fixing this would require changing a lot of code.
        self.serial: Final = serial

    def __str__(self) -> str:
        return str(self.root / str(self.serial))

    def __fspath__(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.base!r}, {self.serial!r})"

    def __eq__(self, other: object) -> bool:
        return Path(self) == Path(other) if isinstance(other, os.PathLike) else NotImplemented

    def __hash__(self) -> int:
        return hash(Path(self))


def _increment_to_next_serial(base: Path) -> int:
    root = VersionedConfigPath.make_root_path(base)
    store = ObjectStore(root / "serial.mk", serializer=DimSerializer())
    with store.locked():
        old_serial: int = store.read_obj(default=0)
        new_serial = old_serial + 1
        store.write_obj(new_serial)
    # TODO: The fact that this can be interpreted as an int
    # is an implementation detail of _increment_to_next_serial.
    # But fixing this would require changing a lot of code.
    return new_serial


def cleanup_old_configs(base: Path) -> None:
    current_config_path = detect_latest_config_path(base)
    root = VersionedConfigPath.make_root_path(base)
    for path in root.iterdir() if root.exists() else []:
        if (
            not path.is_symlink()  # keep "lates" symlink
            and path.is_dir()  # keep "serial.mk"
            and path.resolve() != current_config_path  # keep latest config
        ):
            shutil.rmtree(path)


@contextmanager
def create(base: Path) -> Iterator[ConfigCreationContext]:
    # NOTE:
    # The "latest" symlink points to the last successfully created config.
    # The "serial.mk" file contains the last serial we started to create.
    latest_link_path = VersionedConfigPath.make_latest_path(base)
    current_config_path = latest_link_path.resolve()
    serial = _increment_to_next_serial(base)
    under_construction_path = Path(VersionedConfigPath(base, serial))

    with suppress(FileNotFoundError):
        # this should not exist, but we must be robust.
        shutil.rmtree(under_construction_path)
    under_construction_path.mkdir(parents=True, exist_ok=False)

    try:
        yield ConfigCreationContext(
            path_active=current_config_path,
            path_created=under_construction_path,
            serial_created=serial,
        )
    except Exception:
        raise
    else:
        latest_link_path.unlink(missing_ok=True)
        latest_link_path.symlink_to(under_construction_path.name)
