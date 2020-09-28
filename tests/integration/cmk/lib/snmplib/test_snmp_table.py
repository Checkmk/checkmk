#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.exceptions import MKSNMPError
from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_modes as snmp_modes
import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import OID_BIN, OIDEnd, OID_END_BIN, OID_STRING, SNMPTree


# Found no other way to achieve this
# https://github.com/pytest-dev/pytest/issues/363
@pytest.fixture(scope="module")
def monkeymodule(request):
    from _pytest.monkeypatch import MonkeyPatch  # type: ignore[import] # pylint: disable=import-outside-toplevel
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


# Missing in currently used dump:
# 5 NULL
#68 - Opaque
@pytest.mark.parametrize("type_name,oid,expected_response", [
    ("Counter64", ".1.3.6.1.2.1.4.31.1.1.21.1", "15833452"),
    ("OCTET STRING", ".1.3.6.1.2.1.1.4.0", "SNMP Laboratories, info@snmplabs.com"),
    ("OBJECT IDENTIFIER", ".1.3.6.1.2.1.1.9.1.2.1", ".1.3.6.1.6.3.10.3.1.1"),
    ("IpAddress", ".1.3.6.1.2.1.3.1.1.3.2.1.195.218.254.97", "195.218.254.97"),
    ("Integer32", ".1.3.6.1.2.1.1.7.0", "72"),
    ("Counter32", ".1.3.6.1.2.1.5.1.0", "324"),
    ("Gauge32", ".1.3.6.1.2.1.6.9.0", "9"),
    ("TimeTicks", ".1.3.6.1.2.1.1.3.0", "449613886"),
])
def test_get_data_types(backend, type_name, oid, expected_response):
    response = snmp_modes.get_single_oid(oid, backend=backend)
    assert response == expected_response
    assert isinstance(response, str)

    oid_start, oid_end = oid.rsplit(".", 1)
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=SNMPTree(base=oid_start, oids=[oid_end]),
        backend=backend,
    )

    assert table[0][0] == expected_response
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_not_resolvable(backend):
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(ipaddress="bla.local")
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["1.0", "2.0", "5.0"],
    )

    # TODO: Unify different error messages
    if backend.config.is_inline_snmp_host:
        exc_match = "Failed to initiate SNMP"
    else:
        exc_match = "Unknown host"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            section_name=SectionName("my_Section"),
            oid_info=oid_info,
            backend=backend,
        )


def test_get_simple_snmp_table_wrong_credentials(backend):
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(credentials="dingdong")
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["1.0", "2.0", "5.0"],
    )

    # TODO: Unify different error messages
    if backend.config.is_inline_snmp_host:
        exc_match = "SNMP query timed out"
    else:
        exc_match = "Timeout: No Response from"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            section_name=SectionName("my_Section"),
            oid_info=oid_info,
            backend=backend,
        )


@pytest.mark.parametrize("bulk", [True, False])
def test_get_simple_snmp_table_bulkwalk(backend, bulk):
    backend.config = backend.config.update(is_bulkwalk_host=bulk)
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["1.0", "2.0", "5.0"],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.1",
        oids=["1.0", "2.0", "5.0"],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_oid_end(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=["1", "2", "3", OIDEnd()],
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'1'],
        [u'2', u'eth0', u'6', u'2'],
    ]


def test_get_simple_snmp_table_oid_string(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=["1", "2", "3", OID_STRING],  # type: ignore[list-item]
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'.1.3.6.1.2.1.2.2.1.1.1'],
        [u'2', u'eth0', u'6', u'.1.3.6.1.2.1.2.2.1.1.2'],
    ]


def test_get_simple_snmp_table_oid_bin(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=["1", "2", "3", OID_BIN],  # type: ignore[list-item]
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x01'],
        [u'2', u'eth0', u'6', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x02'],
    ]


def test_get_simple_snmp_table_oid_end_bin(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=["1", "2", "3", OID_END_BIN],  # type: ignore[list-item]
    )
    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01'],
        [u'2', u'eth0', u'6', u'\x02'],
    ]


def test_get_simple_snmp_table_with_hex_str(backend):
    oid_info = SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=["6"],
    )

    table = snmp_table.get_snmp_table(
        section_name=SectionName("my_Section"),
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u''],
        [
            u'\x00\x12yb\xf9@',
        ],
    ]
