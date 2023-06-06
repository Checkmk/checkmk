#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container, Iterable, Iterator, Sequence
from pathlib import Path

from cmk.utils.type_defs import HostName


class AutoQueue(Iterable[HostName]):
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.name)

    def __init__(self, directory: Path | str) -> None:
        self._dir = Path(directory)

    def _ls(self) -> Sequence[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
            return list(self._dir.iterdir())
        except FileNotFoundError:
            return ()

    def __len__(self) -> int:
        return len(self._ls())

    def __iter__(self) -> Iterator[HostName]:
        return (self._host_name(f) for f in self._ls()).__iter__()

    def oldest(self) -> float | None:
        return min((f.stat().st_mtime for f in self._ls()), default=None)

    def remove(self, host_name: HostName) -> None:
        (self._dir / str(host_name)).unlink(missing_ok=True)

    def cleanup(self, *, valid_hosts: Container[HostName], logger: Callable[[str], None]) -> None:
        for host_name in (hn for f in self._ls() if (hn := self._host_name(f)) not in valid_hosts):
            logger(f"  Removing mark '{host_name}' (host not configured)\n")
            self.remove(host_name)
