#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.base.snmp as snmp
import cmk.base.snmp_utils as snmp_utils
from cmk.base.check_api import OID_END, BINARY

from cmk.base.api.agent_based.section_types import (
    SNMPTree,
    OIDEnd,
)

from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees
from testlib.base import Scenario


class _SNMPTestConfig:
    def __init__(self):
        self.character_encoding = "ascii"


class _SNMPTestFactory:
    @staticmethod
    def factory(*_args, **_ka):
        return _SNMPTestBackend()


class _SNMPTestBackend:
    @staticmethod
    def walk(_test_config, fetchoid, **_kw):
        return [("%s.%s" % (fetchoid, r), b"C0FEFE") for r in (1, 2, 3)]


TREE_2TUPLE = ('.1.3.6.1.4.1.13595.2.2.3.1', [OID_END, BINARY("16")])

TREE_3TUPLE = (
    '.1.3.6.1.4.1.3854.1.2.2.1.19.33',
    ["1", "2"],  # TODO: Allow integers here! Some plugins use them!
    ["2.1.2", "2.1.14"],
)

DATA_2TUPLE = [
    ['1', [67, 48, 70, 69, 70, 69]],
    ['2', [67, 48, 70, 69, 70, 69]],
    ['3', [67, 48, 70, 69, 70, 69]],
]

DATA_3TUPLE = [
    ['1.C0FEFE', 'C0FEFE'],
    ['1.C0FEFE', 'C0FEFE'],
    ['1.C0FEFE', 'C0FEFE'],
    ['2.C0FEFE', 'C0FEFE'],
    ['2.C0FEFE', 'C0FEFE'],
    ['2.C0FEFE', 'C0FEFE'],
]


@pytest.mark.parametrize("column", snmp.SPECIAL_COLUMNS)
def test_value_encoding(column):
    assert snmp._value_encoding(column) == "string"


@pytest.mark.parametrize("snmp_info, expected_values", [
    (
        SNMPTree(
            base='.1.3.6.1.4.1.13595.2.2.3.1',
            oids=[
                OIDEnd(),
                snmp_utils.OIDBytes("16"),
            ],
        ),
        DATA_2TUPLE,
    ),
    (TREE_2TUPLE, DATA_2TUPLE),
    (TREE_3TUPLE, DATA_3TUPLE),
    ([TREE_2TUPLE, TREE_3TUPLE], [DATA_2TUPLE, DATA_3TUPLE]),
])
def test_get_snmp_table(monkeypatch, snmp_info, expected_values):
    monkeypatch.setattr(snmp, "SNMPBackendFactory", _SNMPTestFactory)
    monkeypatch.setattr(snmp_utils, "is_snmpv3_host", lambda _x: False)
    snmp_cfg = _SNMPTestConfig()

    def get_all_snmp_tables(info):
        if not isinstance(info, list):
            return snmp.get_snmp_table(snmp_cfg, "unit-test", info)
        return [snmp.get_snmp_table(snmp_cfg, "unit-test", i) for i in info]

    assert get_all_snmp_tables(snmp_info) == expected_values

    # only conduct further tests for legacy spec
    if (isinstance(snmp_info, SNMPTree) or
            isinstance(snmp_info, list) and all(isinstance(t, SNMPTree) for t in snmp_info)):
        return

    # when converting it to the new SNMPTree object, ...
    snmp_info_as_tree_list, layout_recovery = _create_snmp_trees(snmp_info)

    # ... using those to get the snmp data, ...
    reformatted_values = get_all_snmp_tables(snmp_info_as_tree_list)

    # ... and then applying the layout recovery function
    recovered = layout_recovery(reformatted_values)

    # ... we should get the expected data
    assert recovered == expected_values


@pytest.mark.parametrize(
    "encoding,columns,expected",
    [
        (None, [([b'\xc3\xbc'], "string")], [[u"ü"]]),  # utf-8
        (None, [([b'\xc3\xbc'], "binary")], [[[195, 188]]]),  # utf-8
        (None, [([b"\xfc"], "string")], [[u"ü"]]),  # latin-1
        (None, [([b'\xfc'], "binary")], [[[252]]]),  # latin-1
        ("utf-8", [([b'\xc3\xbc'], "string")], [[u"ü"]]),
        ("latin1", [([b'\xfc'], "string")], [[u"ü"]]),
        ("cp437", [([b'\x81'], "string")], [[u"ü"]]),
    ])
def test_sanitize_snmp_encoding(monkeypatch, encoding, columns, expected):
    ts = Scenario().add_host("localhost")
    ts.set_ruleset("snmp_character_encodings", [
        (encoding, [], config.ALL_HOSTS, {}),
    ])
    config_cache = ts.apply(monkeypatch)

    snmp_config = config_cache.get_host_config("localhost").snmp_config("")
    assert snmp._sanitize_snmp_encoding(snmp_config, columns) == expected


def test_is_bulkwalk_host(monkeypatch):
    ts = Scenario().set_ruleset("bulkwalk_hosts", [
        ([], ["localhost"], {}),
    ])
    ts.add_host("abc")
    ts.add_host("localhost")
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_host_config("abc").snmp_config("").is_bulkwalk_host is False
    assert config_cache.get_host_config("localhost").snmp_config("").is_bulkwalk_host is True
