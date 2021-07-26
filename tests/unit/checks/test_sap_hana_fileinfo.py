#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import collections

from tests.testlib import Check
from .checktestlib import MockHostExtraConf
from cmk.utils.type_defs import CheckPluginName
from cmk.base.item_state import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Metric

FileinfoItem = collections.namedtuple("FileinfoItem", "name missing failed size time")


@pytest.mark.parametrize("item, parsed, expected_result", [
    (
        "file1234.txt",
        {},
        [Result(state=State.UNKNOWN, summary='Missing reference timestamp')],
    ),
    (
        "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
        {
            "reftime": 1563288717,
            "files": {
                "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                    name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                    missing=False,
                    failed=False,
                    size=2414,
                    time=1415625918),
            }
        },
        [
            Result(state=State.OK, summary='Size: 2414 B'),
            Metric('size', 2414.0),
            Result(state=State.OK, summary='Age: 4.7 y'),
            Metric('age', 147662799.0)
        ],
    ),
])
def test_sap_hana_fileinfo(fix_register, item, parsed, expected_result):
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo")]
    result = list(plugin.check_function(item=item, params={}, section=parsed))

    assert result == expected_result


@pytest.mark.parametrize("item, parsed", [
    (
        "file1234.txt",
        {
            "reftime": 1563288717,
            "files": {}
        },
    ),
])
def test_sap_hana_fileinfo_stale(fix_register, item, parsed):
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo")]
    with pytest.raises(MKCounterWrapped) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."


@pytest.mark.parametrize("item, parsed, params, expected_result", [
    (
        "file1234.txt",
        {},
        {},
        [Result(state=State.UNKNOWN, summary='Missing reference timestamp')],
    ),
    ("C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7", {
        "reftime": 1563288717,
        "files": {
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                missing=False,
                failed=False,
                size=2414,
                time=1415625918),
        }
    }, {}, [Result(state=State.UNKNOWN, summary='No group pattern found.')]),
])
def test_sap_hana_fileinfo_groups(fix_register, item, parsed, params, expected_result):
    fileinfo_groups_check = Check('fileinfo.groups')
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]

    def mock_host_extra_conf(_hostname, _rulesets):
        return []

    with MockHostExtraConf(fileinfo_groups_check, mock_host_extra_conf, 'host_extra_conf'):
        result = list(plugin.check_function(item=item, params=params, section=parsed))

    assert result == expected_result


@pytest.mark.parametrize("item, parsed", [
    (
        "file1234.txt",
        {
            "reftime": 1563288717,
            "files": {}
        },
    ),
])
def test_sap_hana_fileinfo_groups_stale(fix_register, item, parsed):
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_fileinfo_groups")]
    with pytest.raises(MKCounterWrapped) as e:
        list(plugin.check_function(item=item, params={}, section=parsed))

    assert e.value.args[0] == "Login into database failed."
