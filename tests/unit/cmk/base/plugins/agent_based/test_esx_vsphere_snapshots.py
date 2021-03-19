#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest  # mypy: ignore
from freezegun import freeze_time  # type: ignore[import]
from cmk.base.plugins.agent_based.esx_vsphere_snapshot import (
    Section,
    Snapshot,
    check_snapshots,
    check_snapshots_summary,
    parse_esx_vsphere_snapshots,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils.esx_vsphere import SectionVM


def test_parse_esx_vsphere_snapshots():
    assert parse_esx_vsphere_snapshots([['{"time": 0, "state": "On", "name": "foo"}']
                                       ]) == [Snapshot(time=0, state='On', name='foo')]


@freeze_time("2020-11-23")
def test_check_snapshots_summary(monkeypatch):
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert list(
        check_snapshots_summary(
            {},
            [
                Snapshot(5234560, 'poweredOn', 'PC1'),
                Snapshot(2087850, 'poweredOff', 'PC2'),
            ],
        )) == [
            Result(state=State.OK, summary='Count: 2'),
            Result(state=State.OK, summary='Powered on: PC1'),
            Result(state=State.OK, summary='Latest: PC1 Mar 02 1970 14:02:40'),
            Result(state=State.OK, notice='Age of latest: 50 years 278 days'),
            Result(state=State.OK, summary='Oldest: PC2 Jan 25 1970 03:57:30'),
            Result(state=State.OK, notice='Age of oldest: 50 years 314 days'),
        ]


@freeze_time("2020-11-23")
def test_check_snapshots(monkeypatch):
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert list(
        check_snapshots(
            {},
            {'snapshot.rootSnapshotList': ['871', '1605626114', 'poweredOn', 'Snapshotname']},
        )) == [
            Result(state=State.OK, summary='Count: 1'),
            Result(state=State.OK, summary='Powered on: Snapshotname'),
            Result(state=State.OK, summary='Latest: Snapshotname Nov 17 2020 15:15:14'),
            Result(state=State.OK, notice='Age of latest: 5 days 8 hours'),
            Result(state=State.OK, notice='Age of oldest: 5 days 8 hours'),
        ]
