#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.aix.agent_based.aix_lvm import (
    check_aix_lvm,
    discover_aix_lvm,
    parse_aix_lvm,
    Section,
)

_HEADER = [
    ["rootvg:"],
    ["LV", "NAME", "TYPE", "LPs", "PPs", "PVs", "LV", "STATE", "MOUNT", "POINT"],
]


def _section(*volumes: list[str]) -> Section:
    return parse_aix_lvm(_HEADER + list(volumes))


def test_parse_aix_lvm_groups_volumes_by_volume_group() -> None:
    string_table: StringTable = _HEADER + [
        ["hd5", "boot", "1", "2", "2", "closed/syncd", "N/A"],
        ["hd4", "jfs2", "1", "2", "2", "open/syncd", "/"],
    ]

    section = parse_aix_lvm(string_table)

    assert section == {
        "rootvg": {
            "hd5": ("boot", 1, 2, 2, "closed", "syncd", None),
            "hd4": ("jfs2", 1, 2, 2, "open", "syncd", "/"),
        }
    }


def test_discover_aix_lvm_yields_one_service_per_volume() -> None:
    section = _section(
        ["hd5", "boot", "1", "2", "2", "closed/syncd", "N/A"],
        ["hd4", "jfs2", "1", "2", "2", "open/syncd", "/"],
    )

    assert list(discover_aix_lvm(section)) == [
        Service(item="rootvg/hd5"),
        Service(item="rootvg/hd4"),
    ]


# fmt: off
@pytest.mark.parametrize(
    "volume",
    [
        pytest.param(["hd4", "jfs2", "1", "2", "2", "open/syncd", "/"], id="aligned mirror"),
        pytest.param(["lg_dumplv", "sysdump", "6", "6", "1", "open/syncd", "N/A"], id="unmirrored"),
        pytest.param(["hd5", "boot", "1", "2", "2", "closed/syncd", "N/A"], id="closed boot volume"),
    ],
)
# fmt: on
def test_check_aix_lvm_healthy_volume_is_ok(volume: list[str]) -> None:
    section = _section(volume)

    assert list(check_aix_lvm(f"rootvg/{volume[0]}", section)) == [
        Result(state=State.OK, summary="LV is open/syncd")
    ]


def test_check_aix_lvm_closed_volume_warns() -> None:
    section = _section(["hd9var", "jfs2", "3", "6", "2", "closed/syncd", "/var"])

    assert list(check_aix_lvm("rootvg/hd9var", section)) == [
        Result(state=State.WARN, summary="LV is not opened(!)")
    ]


def test_check_aix_lvm_stale_volume_is_crit() -> None:
    section = _section(["hd2", "jfs2", "5", "10", "2", "open/stale", "/usr"])

    assert list(check_aix_lvm("rootvg/hd2", section)) == [
        Result(state=State.CRIT, summary="LV is not in sync state(!!)")
    ]


def test_check_aix_lvm_mirror_on_one_physical_volume_warns() -> None:
    section = _section(["lvwork", "jfs2", "2", "4", "1", "open/syncd", "/work"])

    assert list(check_aix_lvm("rootvg/lvwork", section)) == [
        Result(state=State.WARN, summary="LV Mirrors are misaligned between physical volumes(!)")
    ]


def test_check_aix_lvm_reports_all_problems_at_worst_state() -> None:
    section = _section(["hd3", "jfs2", "2", "4", "2", "closed/stale", "/tmp"])

    assert list(check_aix_lvm("rootvg/hd3", section)) == [
        Result(state=State.CRIT, summary="LV is not opened(!), LV is not in sync state(!!)")
    ]


def test_check_aix_lvm_missing_volume_is_unknown() -> None:
    section = _section(["hd4", "jfs2", "1", "2", "2", "open/syncd", "/"])

    assert list(check_aix_lvm("rootvg/hd1", section)) == [
        Result(state=State.UNKNOWN, summary="no such volume found")
    ]
