#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check


@pytest.mark.parametrize("info, expected_result", [([
    ["[[HXE", "90]]"],
    ["mode:", "primary"],
    ["systemReplicationStatus:", "10"],
    ["this", "system", "is", "not", "a", "system", "replication", "site"],
], {
    "HXE 90": {
        "sys_repl_status": "10",
        "mode": "primary"
    }
})])
def test_parse_sap_hana_replication_status(info, expected_result):
    result = Check("sap_hana_replication_status").run_parse(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE", "90]]"],
        ["mode:", "primary"],
        ["systemReplicationStatus:", "12"],
        ["this", "system", "is", "not", "a", "system", "replication", "site"],
    ], [("HXE 90", {})]),
    ([
        ["[[HXE", "90]]"],
        ["mode:", "primary"],
        ["systemReplicationStatus:", "10"],
        ["this", "system", "is", "not", "a", "system", "replication", "site"],
    ], []),
])
def test_inventory_sap_hana_replication_status(info, expected_result):
    section = Check("sap_hana_replication_status").run_parse(info)
    result = Check("sap_hana_replication_status").run_discovery(section)
    assert list(result) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90",
        [
            ["[[HXE", "90]]"],
            ["mode:", "primary"],
            ["systemReplicationStatus:", "12"],
            ["this", "system", "is", "not", "a", "system", "replication", "site"],
        ],
        [(0, "System replication: passive")],
    ),
    (
        "HXE 90",
        [
            ["[[HXE", "90]]"],
            ["mode:", "primary"],
            ["systemReplicationStatus:", "88"],
            ["this", "system", "is", "not", "a", "system", "replication", "site"],
        ],
        [(3, "System replication: unknown[88]")],
    ),
])
def test_check_sap_hana_replication_status(item, info, expected_result):
    section = Check("sap_hana_replication_status").run_parse(info)
    result = Check("sap_hana_replication_status").run_check(item, {}, section)
    assert list(result) == expected_result