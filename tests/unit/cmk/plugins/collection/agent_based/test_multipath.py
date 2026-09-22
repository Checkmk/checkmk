#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Final

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.multipath import (
    check_multipath,
    discover_multipath,
    parse_multipath,
)
from cmk.plugins.lib.multipath import Group, Section

STRING_TABLE: Final = [
    # First paths
    ["ORA_ZAPPL2T_DATA_3", "(3600601604d40310047cf93ce66f7e111)", "dm-67", "DGC,RAID", "5"],
    ["size=17G", "features='1", "queue_if_no_path'", "hwhandler='1", "alua'", "wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["| |-", "3:0:1:54", "sddz", "128:16 ", "active", "undef", "running"],
    ["|", "`-", "5:0:1:54", "sdkb", "65:496", "active", "undef", "running"],
    ["`-+-", "policy='round-robin", "0'", "prio=0", "status=enabled"],
    ["|-", "5:0:0:54", "sdbd", "67:112", "active", "undef", "running"],
    ["`-", "3:0:0:54", "sdhf", "133:80", "active", "undef", "running"],
    # Second paths
    ["ORA_UC41T_OLOG_1", "(prefix.3600601604d403100912ab0b365f7e111)", "dm-112", "DGC,RAID", "5"],
    ["size=17G features='1 queue_if_no_path' hwhandler='1 alua' wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["|", "|-", "5:0:0:77", "sdew", "129:128", "active", "undef", "running"],
    # broken paths:
    [
        "BROKEN_PATH",
        "(broken_paths)",
        "dm-67",
        "DGC,RAID",
        "5",
    ],
    ["size=17G", "features='1", "queue_if_no_path'", "hwhandler='1", "alua'", "wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["|-", "5:0:0:54", "sdbd", "67:112", "broken", "undef", "running"],
    ["`-", "3:0:0:54", "sdhf", "133:80", "broken", "undef", "running"],
]


def _agent_output(text: str) -> list[list[str]]:
    return [line.split() for line in text.splitlines()]


SIX_PATHS: Final = _agent_output(
    """\
data01 (360000970000297700123533030303734) dm-7 EMC,SYMMETRIX
size=8.0T features='1 queue_if_no_path' hwhandler='0' wp=rw
`-+- policy='service-time 0' prio=0 status=active
  |- 5:0:9:123  sdax 67:16  active undef running
  |- 5:0:0:123  sdao 66:128 active undef running
  |- 5:0:5:123  sdbe 67:128 active undef running
  |- 4:0:0:123  sdg  8:96   active undef running
  |- 4:0:5:123  sdt  65:48  active undef running
  `- 4:0:12:123 sdag 66:0   active undef running
"""
)

# The same device after three paths vanished from the output entirely
# (as opposed to still being listed with a non-active state).
THREE_PATHS: Final = _agent_output(
    """\
data01 (360000970000297700123533030303734) dm-7 EMC,SYMMETRIX
size=8.0T features='1 queue_if_no_path' hwhandler='0' wp=rw
`-+- policy='service-time 0' prio=0 status=active
  |- 4:0:0:123  sdg  8:96   active undef running
  |- 4:0:5:123  sdt  65:48  active undef running
  `- 4:0:12:123 sdag 66:0   active undef running
"""
)


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_multipath(STRING_TABLE)


def test_parse_multipath_section_keys(section: Section) -> None:
    assert set(section.keys()) == {
        "3600601604d40310047cf93ce66f7e111",
        "prefix.3600601604d403100912ab0b365f7e111",
        "broken_paths",
    }


@pytest.mark.parametrize(
    "item,expected",
    [
        (
            "3600601604d40310047cf93ce66f7e111",
            Group(
                paths=["sddz", "sdkb", "sdbd", "sdhf"],
                broken_paths=[],
                luns=[
                    "3:0:1:54(sddz)",
                    "5:0:1:54(sdkb)",
                    "5:0:0:54(sdbd)",
                    "3:0:0:54(sdhf)",
                ],
                uuid="3600601604d40310047cf93ce66f7e111",
                state="prio=0status=enabled",
                numpaths=4,
                device="dm-67",
                alias="ORA_ZAPPL2T_DATA_3",
            ),
        ),
        (
            "prefix.3600601604d403100912ab0b365f7e111",
            Group(
                paths=["sdew"],
                broken_paths=[],
                luns=["5:0:0:77(sdew)"],
                uuid="prefix.3600601604d403100912ab0b365f7e111",
                state="prio=0status=active",
                numpaths=1,
                device="dm-112",
                alias="ORA_UC41T_OLOG_1",
            ),
        ),
        (
            "broken_paths",
            Group(
                paths=["sdbd", "sdhf"],
                broken_paths=[
                    "5:0:0:54(sdbd)",
                    "3:0:0:54(sdhf)",
                ],
                luns=[
                    "5:0:0:54(sdbd)",
                    "3:0:0:54(sdhf)",
                ],
                uuid="broken_paths",
                state="prio=0status=active",
                numpaths=2,
                device="dm-67",
                alias="BROKEN_PATH",
            ),
        ),
    ],
)
def test_parse_multipath_groups(
    item: str,
    expected: Group,
    section: Section,
) -> None:
    assert section[item] == expected


def test_discovery_stores_current_path_count(section: Section) -> None:
    assert sorted(discover_multipath({"use_alias": False}, section)) == [
        Service(item="3600601604d40310047cf93ce66f7e111", parameters={"discovered_paths": 4}),
        Service(item="broken_paths", parameters={"discovered_paths": 2}),
        Service(
            item="prefix.3600601604d403100912ab0b365f7e111", parameters={"discovered_paths": 1}
        ),
    ]


def test_check_paths_vanished_since_discovery_is_warn() -> None:
    item = "360000970000297700123533030303734"
    (service,) = discover_multipath({"use_alias": False}, parse_multipath(SIX_PATHS))

    results = list(check_multipath(item, service.parameters, parse_multipath(THREE_PATHS)))

    assert results == [
        Result(state=State.OK, summary="(data01): Paths active: 100.00%"),
        Result(state=State.WARN, summary="3 of 3 (expected: 6)"),
    ]


def test_check_configured_path_count_takes_precedence_over_discovered_count() -> None:
    results = list(
        check_multipath(
            "360000970000297700123533030303734",
            {"discovered_paths": 6, "levels": 3},
            parse_multipath(THREE_PATHS),
        )
    )

    assert Result(state=State.OK, summary="3 of 3 (expected: 3)") in results


def test_check_percent_levels(section: Section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            # lower levels. these make no sense, but we want to see a WARN.
            {"levels": (110.0, 40.0)},
            section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 100.00% (warn/crit below 110.00%/40.00%)",
        ),
        Result(
            state=State.OK,
            summary="4 of 4",
        ),
    ]


@pytest.mark.parametrize(
    "levels,state",
    [
        (3, State.WARN),  # Actual level is higher then expected so the state is WARN
        (4, State.OK),  # Actual level
        (5, State.CRIT),  # Actual level is lower then expected so the state is CRIT
    ],
)
def test_check_count_levels(levels: int, state: State, section: Section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            {"levels": levels},
            section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 100.00%",
        ),
        Result(
            state=state,
            summary=f"4 of 4 (expected: {levels})",
        ),
    ]


@pytest.mark.parametrize(
    "item,state,summary",
    [
        ("3600601604d40310047cf93ce66f7e111", State.OK, "4 of 4 (expected: 4)"),
        # WARN cause no rules are present, othervise it will be CRIT
        ("broken_paths", State.WARN, "0 of 2 (expected: 2)"),
    ],
)
def test_check_count_levels_no_configuration_uses_total_paths(
    item: str, state: State, summary: str, section: Section
) -> None:
    results = list(
        check_multipath(
            item,
            {},
            section,
        )
    )
    assert (
        Result(
            state=state,
            summary=summary,
        )
        in results
    )


def test_check_branch_broken_paths_result_added_with_levels_int(section: Section) -> None:
    assert list(
        check_multipath(
            "broken_paths",
            {"levels": 2},
            section,
        )
    ) == [
        Result(state=State.OK, summary="(BROKEN_PATH): Paths active: 0%"),
        Result(state=State.CRIT, summary="0 of 2 (expected: 2)"),
        Result(state=State.OK, summary="Broken paths: 5:0:0:54(sdbd),3:0:0:54(sdhf)"),
    ]


def test_check_returns_nothing_for_unknown_item(section: Section) -> None:
    assert list(check_multipath("does_not_exist", {"levels": 1}, section)) == []


def test_check_multipath_numpaths_zero_does_not_crash() -> None:
    section: Section = {
        "empty": Group(
            paths=[],
            broken_paths=[],
            luns=[],
            uuid="empty",
            state="prio=0status=active",
            numpaths=0,
            device="dm-0",
            alias="empty_group",
        )
    }
    # Must not raise ZeroDivisionError.
    assert list(check_multipath("empty", {}, section))


def test_check_branch_broken_paths_result_added_with_levels_tuple(section: Section) -> None:
    assert list(
        check_multipath(
            "broken_paths",
            {"levels": (110.0, 40.0)},
            section,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="(BROKEN_PATH): Paths active: 0% (warn/crit below 110.00%/40.00%)",
        ),
        Result(
            state=State.OK,
            summary="0 of 2",
        ),
        Result(state=State.OK, summary="Broken paths: 5:0:0:54(sdbd),3:0:0:54(sdhf)"),
    ]


def test_ok_summary_diff_with_default_levels_vs_none(section: Section) -> None:
    item = "3600601604d40310047cf93ce66f7e111"
    default_levels = section[item].numpaths

    out_with_default = list(
        check_multipath(
            item,
            {"levels": default_levels},
            section,
        )
    )

    out_with_none = list(
        check_multipath(
            item,
            {},
            section,
        )
    )

    assert out_with_default == out_with_none


@pytest.mark.parametrize(
    "params",
    [{"levels": 3}, {"levels": (110.0, 40.0)}, {}],
)
def test_check_broken_paths_always_called(
    params: Mapping[str, int | tuple[float, float]], section: Section
) -> None:
    assert list(
        check_multipath(
            "broken_paths",
            params,
            section,
        )
    )[-1] == Result(
        state=State.OK,
        summary="Broken paths: 5:0:0:54(sdbd),3:0:0:54(sdhf)",
    )
