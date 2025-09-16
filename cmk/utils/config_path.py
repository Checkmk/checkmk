#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fetcher config path manipulation."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final, Self

from cmk.ccc.store import DimSerializer, ObjectStore

__all__ = ["VersionedConfigPath"]


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
        self.latest: Final = self.make_latest_path(base)
        self.serial: Final = serial

    def __str__(self) -> str:
        return str(self.root / str(self.serial))

    def __fspath__(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.serial})"

    def __eq__(self, other: object) -> bool:
        return Path(self) == Path(other) if isinstance(other, os.PathLike) else NotImplemented

    def __hash__(self) -> int:
        return hash(Path(self))

    @classmethod
    def next(cls, base: Path) -> Self:
        root = cls.make_root_path(base)
        store = ObjectStore(root / "serial.mk", serializer=DimSerializer())
        with store.locked():
            old_serial: int = store.read_obj(default=0)
            new_serial = old_serial + 1
            store.write_obj(new_serial)
        return cls(base, new_serial)

    def previous_config_path(self) -> VersionedConfigPath:
        return VersionedConfigPath(self.root, self.serial - 1)

    @contextmanager
    def create(self, *, is_cmc: bool) -> Iterator[None]:
        if not is_cmc:  # CMC manages the configs on its own.
            for path in self.root.iterdir() if self.root.exists() else []:
                if (
                    not path.is_symlink()  # keep "lates" symlink
                    and path.is_dir()  # keep "serial.mk"
                    and path.resolve() != self.latest.resolve()  # keep latest config
                ):
                    shutil.rmtree(path)
        Path(self).mkdir(parents=True, exist_ok=True)
        yield
        # TODO(ml) We should probably remove the files that were created
        #          previously and not update `serial.mk` on error.
        # TODO: Should this be in a "finally" or not? Unclear...
        self.latest.unlink(missing_ok=True)
        self.latest.symlink_to(Path(self).name)
