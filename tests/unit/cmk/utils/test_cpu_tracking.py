#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#pylint: disable=redefined-outer-name

import json

import pytest

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
    def test_single_phase(self, set_time):
        set_time(0.0)
        with CPUTracker() as tracker:
            set_time(2.0)

        assert tracker.duration.run_time == 2.0

    def test_split_phase(self, set_time):
        set_time(0.0)
        with CPUTracker() as tracker0:
            set_time(3.0)

        with CPUTracker() as tracker1:
            set_time(5.0)

        with CPUTracker() as tracker2:
            set_time(11.0)

        assert sum(tracker.duration.run_time for tracker in (tracker0, tracker1, tracker2)) == 11.0

    def test_sequential_phases(self, set_time):
        set_time(0.0)
        with CPUTracker() as tracker1:
            set_time(3.0)

        with CPUTracker() as tracker2:
            set_time(5.0)

        with CPUTracker() as tracker3:
            set_time(11.0)

        assert tracker1.duration.run_time == 3.0
        assert tracker2.duration.run_time == 5.0 - 3.0
        assert tracker3.duration.run_time == 11.0 - 5.0

    def test_nested_phases(self, set_time):
        set_time(0.0)
        with CPUTracker() as tracker1:
            set_time(3.0)

            with CPUTracker() as tracker2:
                set_time(5.0)

                with CPUTracker() as tracker3:
                    set_time(13.0)

        assert tracker1.duration.run_time == 13.0
        assert tracker2.duration.run_time == 13.0 - 3.0
        assert tracker3.duration.run_time == 13.0 - 5.0
