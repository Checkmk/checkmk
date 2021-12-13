#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, MutableMapping, Tuple

import pytest

from cmk.utils.exceptions import MKSNMPError
from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_modes as snmp_modes
import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackend,
    SNMPBackendEnum,
    SpecialColumn,
)

INFO_TREE = BackendSNMPTree(
    base=".1.3.6.1.2.1.1",
    oids=[
        BackendOIDSpec("1.0", "string", False),
        BackendOIDSpec("2.0", "string", False),
        BackendOIDSpec("5.0", "string", False),
    ],
)


# Found no other way to achieve this
# https://github.com/pytest-dev/pytest/issues/363
@pytest.fixture(scope="module")
def monkeymodule(request):
    # pylint: disable=import-outside-toplevel
    from _pytest.monkeypatch import MonkeyPatch  # type: ignore[import]

    # pylint: enable=import-outside-toplevel
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


# Missing in currently used dump:
# 5 NULL
# 68 - Opaque
@pytest.mark.parametrize(
    "type_name,oid,expected_response",
    [
        ("Counter64", ".1.3.6.1.2.1.4.31.1.1.21.1", "15833452"),
        ("OCTET STRING", ".1.3.6.1.2.1.1.4.0", "SNMP Laboratories, info@snmplabs.com"),
        ("OBJECT IDENTIFIER", ".1.3.6.1.2.1.1.9.1.2.1", ".1.3.6.1.6.3.10.3.1.1"),
        ("IpAddress", ".1.3.6.1.2.1.3.1.1.3.2.1.195.218.254.97", "195.218.254.97"),
        ("Integer32", ".1.3.6.1.2.1.1.7.0", "72"),
        ("Counter32", ".1.3.6.1.2.1.5.1.0", "324"),
        ("Gauge32", ".1.3.6.1.2.1.6.9.0", "9"),
        ("TimeTicks", ".1.3.6.1.2.1.1.3.0", "449613886"),
    ],
)
def test_get_data_types(
    backend: SNMPBackend, type_name: str, oid: str, expected_response: str
) -> None:
    response = snmp_modes.get_single_oid(oid, backend=backend)
    assert response == expected_response
    assert isinstance(response, str)

    oid_start, oid_end = oid.rsplit(".", 1)
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=BackendSNMPTree(base=oid_start, oids=[BackendOIDSpec(oid_end, "string", False)]),
        backend=backend,
        walk_cache={},
    )

    assert table[0][0] == expected_response
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_not_resolvable(backend: SNMPBackend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config._replace(ipaddress="bla.local")

    # TODO: Unify different error messages
    if backend.config.snmp_backend == SNMPBackendEnum.INLINE:
        exc_match = "Failed to initiate SNMP"
    else:
        exc_match = "Unknown host"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            section_name=SectionName("my_Section"),
            tree=INFO_TREE,
            walk_cache={},
            backend=backend,
        )


def test_get_simple_snmp_table_wrong_credentials(backend: SNMPBackend) -> None:
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config._replace(credentials="dingdong")

    # TODO: Unify different error messages
    if backend.config.snmp_backend == SNMPBackendEnum.INLINE:
        exc_match = "SNMP query timed out"
    else:
        exc_match = "Timeout: No Response from"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            section_name=SectionName("my_Section"),
            tree=INFO_TREE,
            walk_cache={},
            backend=backend,
        )


@pytest.mark.parametrize("bulk", [True, False])
def test_get_simple_snmp_table_bulkwalk(backend: SNMPBackend, bulk: bool) -> None:
    backend.config = backend.config._replace(is_bulkwalk_host=bulk)
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=INFO_TREE,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        [
            "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686",
            ".1.3.6.1.4.1.8072.3.2.10",
            "new system name",
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_fills_cache(backend: SNMPBackend) -> None:

    walk_cache: MutableMapping[str, Tuple[bool, List[Tuple[str, bytes]]]] = {}

    _ = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=INFO_TREE,
        walk_cache=walk_cache,
        backend=backend,
    )

    assert sorted(walk_cache) == [
        ".1.3.6.1.2.1.1.1.0",
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.2.1.1.5.0",
    ]


def test_get_simple_snmp_table(backend: SNMPBackend) -> None:
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=INFO_TREE,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        [
            "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686",
            ".1.3.6.1.4.1.8072.3.2.10",
            "new system name",
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_oid_end(backend: SNMPBackend) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.END, "string", False),
        ],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=oid_info,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        ["1", "lo", "24", "1"],
        ["2", "eth0", "6", "2"],
    ]


def test_get_simple_snmp_table_oid_string(backend: SNMPBackend) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.STRING, "string", False),
        ],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=oid_info,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        ["1", "lo", "24", ".1.3.6.1.2.1.2.2.1.1.1"],
        ["2", "eth0", "6", ".1.3.6.1.2.1.2.2.1.1.2"],
    ]


def test_get_simple_snmp_table_oid_bin(backend: SNMPBackend) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.BIN, "string", False),
        ],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=oid_info,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        ["1", "lo", "24", "\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x01"],
        ["2", "eth0", "6", "\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x02"],
    ]


def test_get_simple_snmp_table_oid_end_bin(backend: SNMPBackend) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.END_BIN, "string", False),
        ],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=oid_info,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        ["1", "lo", "24", "\x01"],
        ["2", "eth0", "6", "\x02"],
    ]


def test_get_simple_snmp_table_with_hex_str(backend: SNMPBackend) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=[BackendOIDSpec("6", "string", False)],
    )

    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        tree=oid_info,
        walk_cache={},
        backend=backend,
    )

    assert table == [
        [""],
        [
            "\x00\x12yb\xf9@",
        ],
    ]
