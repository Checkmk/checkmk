#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.cpu_tracking as cpu_tracking


def test_cpu_tracking_initial_times():
    assert cpu_tracking.get_times() == {}


def test_cpu_tracking_initial_state():
    assert cpu_tracking._is_not_tracking()


def test_pop_without_tracking():
    assert cpu_tracking._is_not_tracking()
    cpu_tracking.pop_phase()
    assert cpu_tracking._is_not_tracking()


def test_push_without_tracking():
    cpu_tracking.push_phase("bla")
    assert cpu_tracking._is_not_tracking()


def test_cpu_tracking_simple(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    assert cpu_tracking.get_times() == {}
    monkeypatch.setattr("time.time", lambda: 1.0)
    cpu_tracking.end()

    times = cpu_tracking.get_times()

    assert len(times) == 2
    assert len(times["TOTAL"]) == 5
    assert times["TOTAL"][4] == 1.0
    assert times["busy"][4] == 1.0


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

    assert times["TOTAL"][4] == 7.0
    assert times["busy"][4] == 2.0
    assert times["snmp"][4] == 2.0
    assert times["agent"][4] == 3.0


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
    assert times["hello"][4] == 42.0


def test_cpu_tracking_add_times(monkeypatch):
    monkeypatch.setattr("time.time", lambda: 0.0)
    cpu_tracking.start("busy")
    monkeypatch.setattr("time.time", lambda: 2.0)

    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 5.0)
    cpu_tracking.pop_phase()

    cpu_tracking.push_phase("agent")
    monkeypatch.setattr("time.time", lambda: 7.0)
    cpu_tracking.pop_phase()

    cpu_tracking.end()

    times = cpu_tracking.get_times()
    assert len(times) == 3

    assert times["TOTAL"][4] == 7.0
    assert times["busy"][4] == 2.0
    assert times["agent"][4] == 5.0
