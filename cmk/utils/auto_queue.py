#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override"

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Final

from cmk.ccc.hostaddress import HostName


class AutoQueue(Iterable[HostName]):
    def __init__(self, directory: Path) -> None:
        self.path: Final = directory

    def _ls(self) -> Sequence[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
            return list(self.path.iterdir())
        except FileNotFoundError:
            return ()

    def __len__(self) -> int:
        return len(self._ls())

    def __iter__(self) -> Iterator[HostName]:
        return (HostName(f.name) for f in self._ls()).__iter__()

    def _host_path(self, host_name: HostName) -> Path:
        return self.path / host_name

    def add(self, host_name: HostName) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        file_path = self._host_path(host_name)
        if not file_path.exists():
            file_path.touch()

    def remove(self, host_name: HostName) -> None:
        self._host_path(host_name).unlink(missing_ok=True)

    def oldest(self) -> float | None:
        return min((f.stat().st_mtime for f in self._ls()), default=None)
