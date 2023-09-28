#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence

import pytest
from freezegun import freeze_time

from tests.unit.cmk.base.plugins.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.esx_vsphere_snapshot import (
    check_snapshots,
    check_snapshots_summary,
    parse_esx_vsphere_snapshots,
    Section,
    Snapshot,
)
from cmk.base.plugins.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm
from cmk.base.plugins.agent_based.utils.esx_vsphere import ESXVm


def test_parse_esx_vsphere_snapshots():
    assert parse_esx_vsphere_snapshots(
        [['{"time": 0, "state": "On", "name": "foo", "vm": "bar"}']]
    ) == [Snapshot(time=0, state="On", name="foo", vm="bar")]


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            [
                Snapshot(5234560, "poweredOn", "PC1", "vm_name"),
                Snapshot(2087850, "poweredOff", "PC2", "vm_name"),
            ],
            [
                Result(state=State.OK, summary="Count: 2"),
                Result(state=State.OK, summary="Powered on: vm_name/PC1"),
                Result(state=State.OK, summary="Latest: vm_name/PC1 Mar 02 1970 14:02:40"),
                Result(state=State.OK, notice="Age of latest: 50 years 278 days"),
                Result(state=State.OK, summary="Oldest: vm_name/PC2 Jan 25 1970 03:57:30"),
                Result(state=State.OK, notice="Age of oldest: 50 years 314 days"),
            ],
        ),
        (
            [
                Snapshot(5234560, "poweredOn", "PC1", "vm_name"),
                Snapshot(1606089700, "poweredOff", "PC2", "vm_name"),
            ],
            [
                Result(
                    state=State.WARN,
                    summary="Snapshot with a creation time in future found. Please check your network time synchronisation.",
                ),
            ],
        ),
    ],
)
@freeze_time("2020-11-23")
def test_check_snapshots_summary(
    section: Section, expected_result: CheckResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    result = check_snapshots_summary({}, section)
    assert list(result) == expected_result


@freeze_time("2020-11-23")
def test_check_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert list(
        check_snapshots(
            {},
            _esx_vm_section(["871", "1605626114", "poweredOn", "Snapshotname"]),
        )
    ) == [
        Result(state=State.OK, summary="Count: 1"),
        Result(state=State.OK, summary="Powered on: test_vm_name/Snapshotname"),
        Result(state=State.OK, summary="Latest: test_vm_name/Snapshotname Nov 17 2020 15:15:14"),
        Result(state=State.OK, notice="Age of latest: 5 days 8 hours"),
        Result(state=State.OK, notice="Age of oldest: 5 days 8 hours"),
    ]


@freeze_time("2020-11-23 14:37:00")
def test_check_multi_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    parsed = parse_esx_vsphere_vm(
        [
            [
                "snapshot.rootSnapshotList",
                "1",
                "1363596734",
                "poweredOff",
                "20130318_105600_snapshot_LinuxI|2",
                "1413977827",
                "poweredOn",
                "LinuxI",
                "Testsnapshot",
            ]
        ]
    )
    assert parsed is not None
    assert list(check_snapshots({}, _esx_vm_section(parsed.snapshots))) == [
        Result(state=State.OK, summary="Count: 2"),
        Result(state=State.OK, summary="Powered on: test_vm_name/LinuxI Testsnapshot"),
        Result(
            state=State.OK, summary="Latest: test_vm_name/LinuxI Testsnapshot Oct 22 2014 11:37:07"
        ),
        Result(state=State.OK, notice="Age of latest: 6 years 34 days"),
        Result(
            state=State.OK,
            summary="Oldest: test_vm_name/20130318_105600_snapshot_LinuxI Mar 18 2013 08:52:14",
        ),
        Result(state=State.OK, notice="Age of oldest: 7 years 252 days"),
    ]


@freeze_time("2019-06-22 14:37:00")
def test_check_one_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    parsed = parse_esx_vsphere_vm(
        [
            [
                "snapshot.rootSnapshotList",
                "154",
                "1560322675",
                "poweredOn",
                "VM-Snapshot",
                "12.06.2019",
                "10:56",
                "UTC+02:00",
            ],
        ]
    )
    assert parsed is not None
    assert list(check_snapshots({"age_oldest": (30, 3600)}, _esx_vm_section(parsed.snapshots))) == [
        Result(state=State.OK, summary="Count: 1"),
        Result(
            state=State.OK,
            summary="Powered on: test_vm_name/VM-Snapshot 12.06.2019 10:56 UTC+02:00",
        ),
        Result(
            state=State.OK,
            summary="Latest: test_vm_name/VM-Snapshot 12.06.2019 10:56 UTC+02:00 Jun 12 2019 06:57:55",
        ),
        Result(state=State.OK, notice="Age of latest: 10 days 7 hours"),
        Result(
            state=State.CRIT,
            summary="Age of oldest: 10 days 7 hours (warn/crit at 30 seconds/1 hour 0 minutes)",
        ),
        Metric("age_oldest", 891545.0, levels=(30.0, 3600.0), boundaries=(0.0, None)),
    ]


@freeze_time("2022-06-22")
def test_time_reference_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    parsed = parse_esx_vsphere_vm(
        [
            ["snapshot.rootSnapshotList", "732", "1594041788", "poweredOn", "FransTeil2"],
        ]
    )
    assert parsed is not None
    assert list(
        check_snapshots(
            {"age": (86400, 172800), "age_oldest": (86400, 172800)},
            _esx_vm_section(parsed.snapshots),
        )
    ) == [
        Result(state=State.OK, summary="Count: 1"),
        Result(state=State.OK, summary="Powered on: test_vm_name/FransTeil2"),
        Result(state=State.OK, summary="Latest: test_vm_name/FransTeil2 Jul 06 2020 13:23:08"),
        Result(
            state=State.CRIT,
            summary="Age of latest: 1 year 350 days (warn/crit at 1 day 0 hours/2 days 0 hours)",
        ),
        Metric("age", 61814212.0, levels=(86400.0, 172800.0), boundaries=(0.0, None)),
        Result(
            state=State.CRIT,
            summary="Age of oldest: 1 year 350 days (warn/crit at 1 day 0 hours/2 days 0 hours)",
        ),
        Metric("age_oldest", 61814212.0, levels=(86400.0, 172800.0), boundaries=(0.0, None)),
    ]


def _esx_vm_section(snapshots: Sequence[str]) -> ESXVm:
    return esx_vm_section(snapshots=snapshots, name="test_vm_name")
