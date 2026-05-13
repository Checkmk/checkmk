#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from cmk.base.legacy_checks.ibm_svc_host import (
    check_ibm_svc_host,
    discover_ibm_svc_host,
    parse_ibm_svc_host,
)

pytestmark = pytest.mark.checks

# Agent output with header line (newer format, sep(58) → split by ":")
STRING_TABLE_WITH_HEADER = [
    [
        "id",
        "name",
        "port_count",
        "iogrp_count",
        "status",
        "site_id",
        "site_name",
        "host_cluster_id",
        "host_cluster_name",
        "protocol",
        "owner_id",
        "owner_name",
        "portset_id",
        "portset_name",
    ],
    [
        "0",
        "HOST1",
        "4",
        "4",
        "online",
        "1",
        "RZO",
        "5",
        "HV2022",
        "scsi",
        "0",
        "HyperV",
        "64",
        "portset64",
    ],
    [
        "2",
        "HOST2",
        "4",
        "4",
        "online",
        "1",
        "RZO",
        "5",
        "HV2022",
        "scsi",
        "0",
        "HyperV",
        "64",
        "portset64",
    ],
    [
        "3",
        "HOST4",
        "4",
        "4",
        "online",
        "1",
        "RZO",
        "5",
        "HV2022",
        "scsi",
        "0",
        "HyperV",
        "64",
        "portset64",
    ],
    [
        "4",
        "HOST5",
        "4",
        "4",
        "offline",
        "1",
        "RZO",
        "5",
        "HV2022",
        "scsi",
        "0",
        "HyperV",
        "64",
        "portset64",
    ],
    ["5", "TEST", "8", "4", "online", "2", "RZU", "", "", "scsi", "1", "IBMi", "64", "portset64"],
    ["6", "PROD", "8", "4", "online", "1", "RZO", "", "", "scsi", "1", "IBMi", "64", "portset64"],
    [
        "7",
        "HOST7",
        "4",
        "4",
        "online",
        "2",
        "RZU",
        "0",
        "DE-HVBUCLUR2",
        "scsi",
        "2",
        "HVBUCLUR2",
        "64",
        "portset64",
    ],
    [
        "8",
        "HOST8",
        "4",
        "4",
        "online",
        "2",
        "RZU",
        "0",
        "DE-HVBUCLUR2",
        "scsi",
        "2",
        "HVBUCLUR2",
        "64",
        "portset64",
    ],
    [
        "10",
        "HOST3",
        "4",
        "4",
        "offline",
        "1",
        "RZO",
        "5",
        "HV2022",
        "scsi",
        "0",
        "HyperV",
        "64",
        "portset64",
    ],
    [
        "11",
        "PROD_DR",
        "8",
        "4",
        "offline",
        "2",
        "RZU",
        "",
        "",
        "scsi",
        "1",
        "IBMi",
        "64",
        "portset64",
    ],
]

# Agent output without header line (older format, uses dflt_header)
STRING_TABLE_NO_HEADER = [
    ["0", "h_esx01", "2", "4", "degraded"],
    ["1", "host206", "2", "2", "online"],
    ["2", "host105", "2", "2", "online"],
    ["3", "host106", "2", "2", "online"],
]

SECTION_WITH_HEADER = parse_ibm_svc_host(STRING_TABLE_WITH_HEADER)
SECTION_NO_HEADER = parse_ibm_svc_host(STRING_TABLE_NO_HEADER)


@pytest.mark.parametrize(
    "string_table, expected_ids, expected_status",
    [
        pytest.param(
            STRING_TABLE_WITH_HEADER,
            ["0", "2", "3", "4", "5", "6", "7", "8", "10", "11"],
            {"0": "online", "4": "offline", "10": "offline", "11": "offline"},
            id="with_header",
        ),
        pytest.param(
            STRING_TABLE_NO_HEADER,
            ["0", "1", "2", "3"],
            {"0": "degraded", "1": "online"},
            id="no_header",
        ),
    ],
)
def test_parse_ibm_svc_host(
    string_table: list[list[str]],
    expected_ids: list[str],
    expected_status: dict[str, str],
) -> None:
    section = parse_ibm_svc_host(string_table)
    assert list(section.keys()) == expected_ids
    for host_id, status in expected_status.items():
        assert section[host_id][0]["status"] == status


def test_parse_ibm_svc_host_with_header_extra_columns() -> None:
    section = parse_ibm_svc_host(STRING_TABLE_WITH_HEADER)
    host1 = section["0"][0]
    assert host1["name"] == "HOST1"
    assert host1["site_name"] == "RZO"
    assert host1["protocol"] == "scsi"
    assert host1["portset_name"] == "portset64"


@pytest.mark.parametrize(
    "section, expected_services",
    [
        pytest.param(SECTION_WITH_HEADER, [(None, {})], id="non_empty"),
        pytest.param({}, [], id="empty"),
    ],
)
def test_discover_ibm_svc_host(
    section: dict,
    expected_services: list[tuple],
) -> None:
    assert list(discover_ibm_svc_host(section)) == expected_services


@pytest.mark.parametrize(
    "section, params, expected_results",
    [
        pytest.param(
            SECTION_WITH_HEADER,
            {},
            [
                (0, "7 active"),
                (0, "0 inactive", [("inactive", 0, None, None)]),
                (0, "0 degraded", [("degraded", 0, None, None)]),
                (0, "3 offline", [("offline", 3, None, None)]),
                (0, "0 other", [("other", 0, None, None)]),
            ],
            id="no_thresholds",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            {"offline_hosts": (2, 5)},
            [
                (0, "7 active"),
                (0, "0 inactive", [("inactive", 0, None, None)]),
                (0, "0 degraded", [("degraded", 0, None, None)]),
                (1, "3 offline", [("offline", 3, 2, 5)]),
                (0, "0 other", [("other", 0, None, None)]),
            ],
            id="offline_warn",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            # crit=3 matches offline count exactly — must yield CRIT, not WARN
            {"offline_hosts": (2, 3)},
            [
                (0, "7 active"),
                (0, "0 inactive", [("inactive", 0, None, None)]),
                (0, "0 degraded", [("degraded", 0, None, None)]),
                (2, "3 offline", [("offline", 3, 2, 3)]),
                (0, "0 other", [("other", 0, None, None)]),
            ],
            id="offline_crit_takes_priority_over_warn",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            {"active_hosts": (5, 3)},
            [
                (0, "7 active"),
                (0, "0 inactive", [("inactive", 0, None, None)]),
                (0, "0 degraded", [("degraded", 0, None, None)]),
                (0, "3 offline", [("offline", 3, None, None)]),
                (0, "0 other", [("other", 0, None, None)]),
            ],
            id="active_ok_above_thresholds",
        ),
        pytest.param(
            SECTION_NO_HEADER,
            {"always_ok": False},
            [
                (
                    0,
                    "3 active, 0 inactive",
                    [
                        ("active", 3),
                        ("inactive", 0),
                        ("degraded", 1),
                        ("offline", 0),
                        ("other", 0),
                    ],
                ),
                (1, "1 degraded"),
            ],
            id="always_ok_false_with_degraded",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            {"always_ok": True},
            [
                (
                    0,
                    "7 active, 0 inactive",
                    [
                        ("active", 7),
                        ("inactive", 0),
                        ("degraded", 0),
                        ("offline", 3),
                        ("other", 0),
                    ],
                ),
                (0, "3 offline"),
            ],
            id="always_ok_true_suppresses_offline",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            {"always_ok": False},
            [
                (
                    0,
                    "7 active, 0 inactive",
                    [
                        ("active", 7),
                        ("inactive", 0),
                        ("degraded", 0),
                        ("offline", 3),
                        ("other", 0),
                    ],
                ),
                (2, "3 offline"),
            ],
            id="always_ok_false_with_offline",
        ),
        pytest.param(
            SECTION_WITH_HEADER,
            None,
            [
                (
                    0,
                    "7 active, 0 inactive",
                    [
                        ("active", 7),
                        ("inactive", 0),
                        ("degraded", 0),
                        ("offline", 3),
                        ("other", 0),
                    ],
                ),
                (2, "3 offline"),
            ],
            id="none_params_treated_as_always_ok_false",
        ),
    ],
)
def test_check_ibm_svc_host(
    section: dict,
    params: Any,
    expected_results: list[tuple],
) -> None:
    assert list(check_ibm_svc_host(None, params, section)) == expected_results
