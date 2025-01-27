#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Iterable, MutableMapping
from pathlib import Path

from cmk.snmplib import SNMPRowInfo

from cmk.fetchers._snmp import WalkCache


class MockWalkCache(WalkCache):
    def __init__(self, mockdata: MutableMapping[str, SNMPRowInfo], path: Path) -> None:
        super().__init__(path, logging.getLogger("test"))
        self.mock_stored_on_fs = mockdata

    def _read_row(self, path: Path) -> SNMPRowInfo:
        return self.mock_stored_on_fs[str(path.name)]

    def _write_row(self, path: Path, rowinfo: SNMPRowInfo) -> None:
        self.mock_stored_on_fs[str(path.name)] = rowinfo

    def _iterfiles(self) -> Iterable[Path]:
        return (Path(k) for k in self.mock_stored_on_fs)


class TestWalkCache:
    def test_oid2name_roundtrip(self) -> None:
        fetchoid, context_hash = ".3.1.4.1.5.9.2.6.5.3.5", "12c3d4a"
        assert (fetchoid, context_hash) == WalkCache._name2oid(
            WalkCache._oid2name(fetchoid, context_hash)
        )

    def test_cache_keeps_stored_data(self, tmp_path: Path) -> None:
        fetchoid, context_hash = ".1.2.3", "12c3d4a"
        path = f"OID{fetchoid}-{context_hash}"
        cache = MockWalkCache({path: [("23", b"43")]}, tmp_path)

        assert not cache

        cache.load()

        assert (fetchoid, "12c3d4a", True) in cache
        cache.save()
        assert path in cache.mock_stored_on_fs
