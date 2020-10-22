#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Tuple
from testlib import Check  # type: ignore[import]
import freezegun  # type: ignore[import]

import pytest  # type: ignore[import]
from checktestlib import CheckResult, assertCheckResultsEqual, MockItemState

# all tests in this file are hp_msa_volume check related
pytestmark = pytest.mark.checks

# ##### hp_msa_volume (health) #########


@pytest.mark.usefixtures("config_load_all_checks")
def test_health_parse_yields_with_volume_name_as_items():
    info = [["volume", "1", "volume-name", "Foo"]]
    expected_yield = {'Foo': {'volume-name': 'Foo'}}
    check = Check("hp_msa_volume")
    parse_result = check.run_parse(info)
    assert parse_result == expected_yield


@pytest.mark.usefixtures("config_load_all_checks")
def test_health_parse_yields_volume_name_as_items_despite_of_durable_id():
    info = [["volume", "1", "durable-id", "Foo 1"], ["volume", "1", "volume-name", "Bar 1"],
            ["volume", "1", "any-key-1", "abc"], ["volume-statistics", "1", "volume-name", "Bar 1"],
            ["volume-statistics", "1", "any-key-2", "ABC"], ["volume", "2", "durable-id", "Foo 2"],
            ["volume", "2", "volume-name", "Bar 2"], ["volume", "2", "any-key-2", "abc"],
            ["volume-statistics", "2", "volume-name", "Bar 2"],
            ["volume-statistics", "2", "any-key-2", "ABC"]]
    check = Check("hp_msa_volume")
    parse_result = check.run_parse(info)
    parsed_items = sorted(parse_result.keys())
    expected_items = ['Bar 1', 'Bar 2']
    assert parsed_items == expected_items


@pytest.mark.usefixtures("config_load_all_checks")
def test_health_discovery_forwards_info():
    info = [["volume", "1", "volume-name", "Foo"]]
    check = Check("hp_msa_volume")
    discovery_result = check.run_discovery(info)
    assert discovery_result == [(info[0], None)]


@pytest.mark.usefixtures("config_load_all_checks")
def test_health_check_accepts_volume_name_and_durable_id_as_item():
    item_1st = "VMFS_01"
    item_2nd = "V4"
    check = Check("hp_msa_volume")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'container-name': u'A',
            u'health': u'OK',
            u'item_type': u'volumes',
            u'raidtype': u'RAID0',
        },
        u'V4': {
            u'durable-id': u'V4',
            u'container-name': u'B',
            u'health': u'OK',
            u'item_type': u'volumes',
            u'raidtype': u'RAID0',
        }
    }
    _, status_message_item_1st = check.run_check(item_1st, None, parsed)
    assert status_message_item_1st == 'Status: OK, container name: A (RAID0)'
    _, status_message_item_2nd = check.run_check(item_2nd, None, parsed)
    assert status_message_item_2nd == 'Status: OK, container name: B (RAID0)'


# ##### hp_msa_volume.df ######


@pytest.mark.usefixtures("config_load_all_checks")
def test_df_discovery_yields_volume_name_as_item():
    parsed = {'Foo': {'durable-id': 'Bar'}}
    expected_yield: Tuple[str, Dict[Any, Any]] = ('Foo', {})
    check = Check("hp_msa_volume.df")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


@pytest.mark.usefixtures("config_load_all_checks")
def test_df_check():
    item_1st = 'VMFS_01'
    params = {'flex_levels': 'irrelevant'}
    check = Check("hp_msa_volume.df")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'virtual-disk-name': u'A',
            u'total-size-numeric': u'4296482816',
            u'allocated-size-numeric': u'2484011008',
            u'raidtype': u'RAID0',
        },
        u'VMFS_02': {
            u'durable-id': u'V4',
            u'virtual-disk-name': u'A',
            u'total-size-numeric': u'4296286208',
            u'allocated-size-numeric': u'3925712896',
            u'raidtype': u'RAID0',
        }
    }
    expected_result = (0, '57.81% used (1.16 of 2.00 TB), trend: +2.43 TB / 24 hours', [
        ('fs_used', 1212896, 1678313.6, 1888102.8, 0, 2097892),
        ('fs_size', 2097892),
        ('fs_used_percent', 57.81498761614039),
        ('growth', 1329829.766497462),
        ('trend', 2551581.1594836353, None, None, 0, 87412.16666666667),
    ])

    with freezegun.freeze_time("2020-07-31 07:00:00"), MockItemState((1596100000, 42)):
        _, trend_result = check.run_check(item_1st, params, parsed)

    assertCheckResultsEqual(CheckResult(trend_result), CheckResult(expected_result))


# #### hp_msa_io.io  #####


@pytest.mark.usefixtures("config_load_all_checks")
def test_io_discovery_yields_summary():
    parsed = {'Foo': {'durable-id': 'Bar'}}
    expected_yield = ('SUMMARY', 'diskstat_default_levels')
    check = Check("hp_msa_volume.io")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


@pytest.mark.usefixtures("config_load_all_checks")
def test_io_check():
    item_1st = 'VMFS_01'
    params = {'flex_levels': 'irrelevant'}
    check = Check("hp_msa_volume.io")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'data-read-numeric': u'23719999539712',
            u'data-written-numeric': u'18093374647808',
            u'virtual-disk-name': u'A',
            u'raidtype': u'RAID0',
        },
        u'VMFS_02': {
            u'durable-id': u'V4',
            u'data-read-numeric': u'49943891507200',
            u'data-written-numeric': u'7384656100352',
            u'virtual-disk-name': u'A',
            u'raidtype': u'RAID0',
        }
    }
    _, read, written = check.run_check(item_1st, params, parsed)
    assertCheckResultsEqual(
        CheckResult(read),
        CheckResult((0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0, None, None)])))
    assertCheckResultsEqual(
        CheckResult(written),
        CheckResult((0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0, None, None)])))
