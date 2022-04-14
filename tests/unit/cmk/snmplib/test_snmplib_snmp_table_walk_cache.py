#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Iterable, MutableMapping

from cmk.utils.type_defs import HostName

from cmk.snmplib.snmp_table import WalkCache
from cmk.snmplib.type_defs import BackendOIDSpec, BackendSNMPTree, SNMPRowInfo


class MockWalkCache(WalkCache):
    def __init__(self, mockdata: MutableMapping[str, SNMPRowInfo]) -> None:
        super().__init__(HostName("testhost"))
        self.mock_stored_on_fs = mockdata

    def _read_row(self, path: Path) -> SNMPRowInfo:
        return self.mock_stored_on_fs[str(path.name)]

    def _write_row(self, path: Path, rowinfo: SNMPRowInfo) -> None:
        self.mock_stored_on_fs[str(path.name)] = rowinfo

    def _iterfiles(self) -> Iterable[Path]:
        return (Path(k) for k in self.mock_stored_on_fs)


class TestWalkCache:
    def test_oid2name_roundtrip(self) -> None:
        fetchoid = ".3.1.4.1.5.9.2.6.5.3.5"
        assert fetchoid == WalkCache._name2oid(WalkCache._oid2name(fetchoid))

    def test_cache_keeps_stored_data(self) -> None:

        fetchoid = ".1.2.3"
        path = f"OID{fetchoid}"
        cache = MockWalkCache({path: [("23", b"43")]})

        assert not cache

        cache.load(
            trees=[
                BackendSNMPTree(
                    base=".1.2",
                    oids=[BackendOIDSpec("3", "string", True)],
                ),
            ],
        )

        assert fetchoid in cache
        cache.save()
        assert path in cache.mock_stored_on_fs

    def test_cache_ignores_non_save_oids(self) -> None:
        """
        If one plugin wants live data, and the other one wants cached
        data, the live data requirement should win.
        """

        fetchoid = ".1.2.3"
        path = f"OID{fetchoid}"
        cache = MockWalkCache({path: [("23", b"42")]})

        assert not cache

        cache.load(
            trees=[
                BackendSNMPTree(
                    base=".1.2",
                    oids=[BackendOIDSpec("3", "string", False)],
                ),
                BackendSNMPTree(
                    base=".1.2",
                    oids=[BackendOIDSpec("3", "string", True)],
                ),
            ]
        )

        assert fetchoid not in cache
