#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, IgnoreResults, Metric, Result, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_snapshot_age import (
    _check_proxmox_ve_snapshot_age_testable,
    check_proxmox_ve_snapshot_age,
    parse_proxmox_ve_snapshot_age,
    SectionSnapshots,
)


@pytest.mark.parametrize(
    "data,expected",
    [
        ('{"snaptimes": []}', SectionSnapshots(snaptimes=[])),
        ('{"snaptimes": [1]}', SectionSnapshots(snaptimes=[1])),
    ],
)
def test_parse_proxmox_ve_snapshot_age(data: str, expected: SectionSnapshots) -> None:
    assert parse_proxmox_ve_snapshot_age([[data]]) == expected


@pytest.mark.parametrize(
    "now,params,section,expected",
    [
        (
            1,
            {"oldest_levels": ("fixed", (604800, 2592000))},
            SectionSnapshots(snaptimes=[]),
            [Result(state=State.OK, summary="No snapshot found")],
        ),
    ],
)
def test_check_proxmox_ve_snapshot_age_no_snapshot(
    now: int | float,
    params: Mapping[str, object],
    section: SectionSnapshots,
    expected: Sequence[IgnoreResults | Metric | Result],
) -> None:
    assert list(check_proxmox_ve_snapshot_age(params, section)) == expected


@pytest.mark.parametrize(
    "params,section_data,expected_result",
    [
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            SectionSnapshots(snaptimes=[96_000]),
            [
                Result(state=State.OK, summary="Oldest: 1 hour 6 minutes"),
                Metric(
                    "oldest_snapshot_age",
                    4000.0,
                    levels=(5000.0, 10000.0),
                    boundaries=(5000.0, 10000.0),
                ),
                Result(state=State.OK, summary="Newest: 1 hour 6 minutes"),
                Metric("newest_snapshot_age", 4000.0),
                Result(state=State.OK, summary="Snapshots: 1"),
            ],
        ),
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            SectionSnapshots(snaptimes=[96_000, 94_000]),
            [
                Result(
                    state=State.WARN,
                    summary="Oldest: 1 hour 40 minutes (warn/crit at 1 hour 23 minutes/2 hours 46 minutes)",
                ),
                Metric(
                    "oldest_snapshot_age",
                    6000.0,
                    levels=(5000.0, 10000.0),
                    boundaries=(5000.0, 10000.0),
                ),
                Result(state=State.OK, summary="Newest: 1 hour 6 minutes"),
                Metric("newest_snapshot_age", 4000.0),
                Result(state=State.OK, summary="Snapshots: 2"),
            ],
        ),
        (
            {
                "oldest_levels": ("fixed", (5000, 10000)),
            },
            SectionSnapshots(snaptimes=[96_000, 94_000, 89_000]),
            [
                Result(
                    state=State.CRIT,
                    summary="Oldest: 3 hours 3 minutes (warn/crit at 1 hour 23 minutes/2 hours 46 minutes)",
                ),
                Metric(
                    "oldest_snapshot_age",
                    11000.0,
                    levels=(5000.0, 10000.0),
                    boundaries=(5000.0, 10000.0),
                ),
                Result(state=State.OK, summary="Newest: 1 hour 6 minutes"),
                Metric("newest_snapshot_age", 4000.0),
                Result(state=State.OK, summary="Snapshots: 3"),
            ],
        ),
    ],
)
def test_check_proxmox_ve_snapshot_age_with_snapshot(
    params: Mapping[str, Any],
    section_data: SectionSnapshots,
    expected_result: CheckResult,
) -> None:
    assert (
        list(_check_proxmox_ve_snapshot_age_testable(100_000, params, section_data.snaptimes))
        == expected_result
    )
