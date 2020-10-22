#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#pylint: disable=redefined-outer-name

import json

import pytest

import cmk.utils.cpu_tracking as cpu_tracking
from cmk.utils.cpu_tracking import Snapshot, CPUTracker


def json_identity(serializable):
    return json.loads(json.dumps(serializable))


@pytest.fixture
def set_time(monkeypatch):
    def setter(value):
        monkeypatch.setattr("time.time", lambda value=value: value)

    return setter


class TestCpuTracking:
    @pytest.fixture
    def null(self):
        return Snapshot.null()

    @pytest.fixture
    def now(self):
        return Snapshot.take()

    def test_eq_neq(self, null, now):
        assert null == Snapshot.null()
        assert null != now
        assert now != null

    def test_add_null_null(self, null):
        assert null + null == null

    def test_add_null_now(self, null, now):
        assert null + now == now

    def test_sub_null_null(self, null):
        assert null - null == null

    def test_sub_now_null(self, now, null):
        assert now - null == now

    def test_sub_now_now(self, now, null):
        assert now - now == null

    def test_json_serialization_null(self, null):
        assert Snapshot.deserialize(json_identity(null.serialize())) == null

    def test_json_serialization_now(self, now):
        assert Snapshot.deserialize(json_identity(now.serialize())) == now


class TestCPUTracker:
    @pytest.fixture
    def tracker(self):
        return CPUTracker()

    def test_serialization(self, tracker):
        tracker["phase0"] = Snapshot.take()
        tracker["phase1"] = Snapshot.take()
        tracker["phase2"] = Snapshot.take()
        assert CPUTracker.deserialize(json_identity(tracker.serialize())) == tracker

    def test_single_phase(self, tracker, set_time):
        set_time(0.0)
        with cpu_tracking.phase(tracker, "phase"):
            set_time(2.0)

        assert len(tracker) == 1
        assert tracker["phase"].run_time == 2.0

    def test_split_phase(self, tracker, set_time):
        set_time(0.0)
        with cpu_tracking.phase(tracker, "phase"):
            set_time(3.0)

        with cpu_tracking.phase(tracker, "phase"):
            set_time(5.0)

        with cpu_tracking.phase(tracker, "phase"):
            set_time(11.0)

        assert len(tracker) == 1
        assert tracker["phase"].run_time == 11.0

    def test_sequential_phases(self, tracker, set_time):
        set_time(0.0)
        with cpu_tracking.phase(tracker, "phase1"):
            set_time(3.0)

        with cpu_tracking.phase(tracker, "phase2"):
            set_time(5.0)

        with cpu_tracking.phase(tracker, "phase3"):
            set_time(11.0)

        assert len(tracker) == 3
        assert tracker["phase1"].run_time == 3.0
        assert tracker["phase2"].run_time == 5.0 - 3.0
        assert tracker["phase3"].run_time == 11.0 - 5.0

    def test_nested_phases(self, tracker, set_time):
        set_time(0.0)
        with cpu_tracking.phase(tracker, "phase1"):
            set_time(3.0)

            with cpu_tracking.phase(tracker, "phase2"):
                set_time(5.0)

                with cpu_tracking.phase(tracker, "phase3"):
                    set_time(13.0)

        assert len(tracker) == 3
        assert tracker["phase1"].run_time == 13.0
        assert tracker["phase2"].run_time == 13.0 - 3.0
        assert tracker["phase3"].run_time == 13.0 - 5.0
