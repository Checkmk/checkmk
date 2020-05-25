#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
import six

import cmk.utils.snmp_table as snmp_table
from cmk.utils.type_defs import OID_BIN, OID_END, OID_END_BIN, OID_STRING, OIDWithColumns

import cmk.base.snmp as snmp
from cmk.base.exceptions import MKSNMPError


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
def test_get_data_types(snmp_config, type_name, oid, expected_response):
    response = snmp.get_single_oid(snmp_config, oid)
    assert response == expected_response
    assert isinstance(response, six.text_type)

    oid_start, oid_end = oid.rsplit(".", 1)
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=(oid_start, [oid_end]),
    )

    assert table[0][0] == expected_response
    assert isinstance(table[0][0], six.text_type)


def test_get_simple_snmp_table_not_resolvable(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(ipaddress="bla.local")

    # TODO: Unify different error messages
    if snmp_config.is_inline_snmp_host:
        exc_match = "Failed to initiate SNMP"
    elif not snmp_config.is_inline_snmp_host:
        exc_match = "Unknown host"
    else:
        raise NotImplementedError()

    with pytest.raises(MKSNMPError, match=exc_match):
        oid_info = (
            ".1.3.6.1.2.1.1",
            ["1.0", "2.0", "5.0"],
        )  # type: OIDWithColumns
        snmp_table.get_snmp_table(
            snmp_config,
            check_plugin_name="",
            oid_info=oid_info,
        )


def test_get_simple_snmp_table_wrong_credentials(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(credentials="dingdong")

    # TODO: Unify different error messages
    if snmp_config.is_inline_snmp_host:
        exc_match = "SNMP query timed out"
    elif not snmp_config.is_inline_snmp_host:
        exc_match = "Timeout: No Response from"
    else:
        raise NotImplementedError()

    with pytest.raises(MKSNMPError, match=exc_match):
        oid_info = (
            ".1.3.6.1.2.1.1",
            ["1.0", "2.0", "5.0"],
        )  # type: OIDWithColumns
        snmp_table.get_snmp_table(
            snmp_config,
            check_plugin_name="",
            oid_info=oid_info,
        )


@pytest.mark.parametrize("bulk", [True, False])
def test_get_simple_snmp_table_bulkwalk(snmp_config, bulk):
    snmp_config = snmp_config.update(is_bulkwalk_host=bulk)
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], six.text_type)


def test_get_simple_snmp_table(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], six.text_type)


def test_get_simple_snmp_table_oid_end(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_END],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [u'1', u'lo', u'24', u'1'],
        [u'2', u'eth0', u'6', u'2'],
    ]


def test_get_simple_snmp_table_oid_string(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_STRING],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [u'1', u'lo', u'24', u'.1.3.6.1.2.1.2.2.1.1.1'],
        [u'2', u'eth0', u'6', u'.1.3.6.1.2.1.2.2.1.1.2'],
    ]


def test_get_simple_snmp_table_oid_bin(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_BIN],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x01'],
        [u'2', u'eth0', u'6', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x02'],
    ]


def test_get_simple_snmp_table_oid_end_bin(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_END_BIN],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01'],
        [u'2', u'eth0', u'6', u'\x02'],
    ]


def test_get_simple_snmp_table_with_hex_str(snmp_config):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        [
            "6",
        ],
    )  # type: OIDWithColumns

    table = snmp_table.get_snmp_table(
        snmp_config,
        check_plugin_name="",
        oid_info=oid_info,
    )

    assert table == [
        [u''],
        [
            u'\x00\x12yb\xf9@',
        ],
    ]
