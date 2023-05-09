#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]


@pytest.fixture(name="string_table")
def snmp_section():
    return [
        ["1", "", "2", "286070", "4294967295"],
        ["2", "", "2", "25753986", "4294967295"],
        ["3", "", "2", "30523320", "4294967295"],
        ["4", "", "2", "15", "4294967295"],
        ["5", "", "2", "15", "4294967295"],
        ["6", "", "2", "17169273", "4294967295"],
    ]


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_hp_proliant_raid_no_snmp_data() -> None:
    check_plugin = Check("hp_proliant_raid")
    assert list(check_plugin.run_discovery({})) == []


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_hp_proliant_raid(string_table,) -> None:
    check_plugin = Check("hp_proliant_raid")
    discovery_results = list(check_plugin.run_discovery(check_plugin.run_parse(string_table)))
    assert discovery_results == [
        ("1", None),
        ("2", None),
        ("3", None),
        ("4", None),
        ("5", None),
        ("6", None),
    ]


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_hp_proliant_raid_item_not_found(string_table,) -> None:
    check_plugin = Check("hp_proliant_raid")
    assert (list(check_plugin.run_check(
        "!111elf",
        {},
        check_plugin.run_parse(string_table),
    )) == [])


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_hp_proliant_raid(string_table,) -> None:
    check_plugin = Check("hp_proliant_raid")
    assert list(check_plugin.run_check(
        "1",
        {},
        check_plugin.run_parse(string_table),
    )) == [
        (0, "Status: OK"),
        (0, "Logical volume size: 279.37 GB"),
    ]


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_hp_proliant_raid_progress_cannot_be_determined() -> None:
    check_plugin = Check("hp_proliant_raid")
    assert list(
        check_plugin.run_check(
            "banana 1",
            {},
            check_plugin.run_parse([
                ["1", "banana", "7", "286070", "4294967295"],
            ]),
        )) == [
            (1, "Status: rebuilding"),
            (0, "Logical volume size: 279.37 GB"),
            (0, "Rebuild: undetermined"),
        ]
