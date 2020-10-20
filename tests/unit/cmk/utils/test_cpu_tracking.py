#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

import cmk.utils.cpu_tracking as cpu_tracking


def json_identity(serializable):
    return json.loads(json.dumps(serializable))


@pytest.fixture(autouse=True, scope="function")
def reset_cpu_tracking(monkeypatch):
    cpu_tracking.reset()


class TestCpuTracking:
    @pytest.fixture
    def null(self):
        return cpu_tracking.Snapshot.null()

    @pytest.fixture
    def now(self):
        return cpu_tracking.Snapshot.take()

    def test_eq_neq(self, null, now):
        assert null == cpu_tracking.Snapshot.null()
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
        assert cpu_tracking.Snapshot.deserialize(json_identity(null.serialize())) == null

    def test_json_serialization_now(self, now):
        assert cpu_tracking.Snapshot.deserialize(json_identity(now.serialize())) == now


def test_cpu_tracking_initial_times():
    assert cpu_tracking.get_times() == {}


def test_cpu_tracking_initial_state():
    assert not cpu_tracking.is_tracking()


def test_pop_without_tracking():
    assert not cpu_tracking.is_tracking()
    cpu_tracking.pop_phase()
    assert not cpu_tracking.is_tracking()


def test_push_without_tracking():
    cpu_tracking.push_phase("bla")
    assert not cpu_tracking.is_tracking()


def test_cpu_tracking_simple(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    assert cpu_tracking.get_times() == {}
    monkeypatch.setattr("time.time", lambda: 1.0)
    cpu_tracking.end()

    times = cpu_tracking.get_times()

    assert len(times) == 2
    assert times["TOTAL"].run_time == 1.0
    assert times["busy"].run_time == 1.0


def test_cpu_tracking_multiple_phases(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    monkeypatch.setattr("time.time", lambda: 2.0)

    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 5.0)
    cpu_tracking.pop_phase()

    cpu_tracking.push_phase("snmp")
    monkeypatch.setattr("time.time", lambda: 7.0)
    cpu_tracking.pop_phase()

    cpu_tracking.end()

    times = cpu_tracking.get_times()
    assert len(times) == 4

    assert times["TOTAL"].run_time == 7.0
    assert times["busy"].run_time == 2.0
    assert times["snmp"].run_time == 2.0
    assert times["agent"].run_time == 3.0


def test_cpu_tracking_decorator(monkeypatch):
    class K:
        cpu_tracking_id = "hello"

        @cpu_tracking.track
        def tracked(self):
            pass

    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("hello")
    monkeypatch.setattr("time.time", lambda: 42.0)
    obj = K()
    obj.tracked()
    cpu_tracking.end()

    times = cpu_tracking.get_times()
    assert times["hello"].run_time == 42.0


def test_cpu_tracking_context_managers(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    with cpu_tracking.execute("busy"):
        monkeypatch.setattr("time.time", lambda: 1.0)
        with cpu_tracking.phase("aa"):
            monkeypatch.setattr("time.time", lambda: 4.0)
        with cpu_tracking.phase("bb"):
            monkeypatch.setattr("time.time", lambda: 9.0)
        monkeypatch.setattr("time.time", lambda: 16.0)

    times = cpu_tracking.get_times()
    assert times["busy"].run_time == 8.0
    assert times["TOTAL"].run_time == 16.0
    assert times["aa"].run_time == 3.0
    assert times["bb"].run_time == 5.0


def test_cpu_tracking_add_times(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    monkeypatch.setattr("time.time", lambda: 2.0)

    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 5.0)
    cpu_tracking.pop_phase()

    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 9.0)
    cpu_tracking.pop_phase()

    cpu_tracking.end()

    times = cpu_tracking.get_times()
    assert len(times) == 3

    assert times["TOTAL"].run_time == 9.0, times["TOTAL"]
    assert times["busy"].run_time == 2.0, times["busy"]
    assert times["agent"].run_time == 7.0, times["agent"]


def test_cpu_tracking_update(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    cpu_tracking.update(
        {
            "busy": cpu_tracking.Snapshot(
                cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                5.0,
            ),
            "agent": cpu_tracking.Snapshot(
                cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                5.0,
            ),
            "test": cpu_tracking.Snapshot(
                cpu_tracking.times_result([1.0, 2.0, 3.0, 4.0, 5.0]),
                5.0,
            ),
            "TOTAL": cpu_tracking.Snapshot(
                cpu_tracking.times_result([3.0, 6.0, 9.0, 12.0, 15.0]),
                15.0,
            ),
        },)
    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 9.0)
    cpu_tracking.pop_phase()

    cpu_tracking.end()
    times = cpu_tracking.get_times()
    assert len(times) == 4

    assert times["TOTAL"].run_time == 24.0  # 15 + 9
    assert times["busy"].run_time == 5.0  # 5 + 0
    assert times["agent"].run_time == 14.0  # 5 + 9
    assert times["test"].run_time == 5.0  # 5
