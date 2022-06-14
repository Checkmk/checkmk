#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.ec.main import Perfcounters

logger = logging.getLogger("cmk.mkeventd")


def test_perfcounters_count() -> None:
    c = Perfcounters(logger)
    assert c._counters["messages"] == 0
    c.count("messages")
    assert c._counters["messages"] == 1

    assert not [(k, v) for k, v in c._counters.items() if k != "messages" and v > 0]


def test_perfcounters_count_time() -> None:
    c = Perfcounters(logger)
    assert "processing" not in c._times
    c.count_time("processing", 1.0)
    assert c._times["processing"] == 1.0
    c.count_time("processing", 1.0)
    assert c._times["processing"] == 1.0
    c.count_time("processing", 5.0)
    assert c._times["processing"] == 1.04


def test_perfcounters_do_statistics(monkeypatch) -> None:
    monkeypatch.setattr("time.time", lambda: 1.0)

    c = Perfcounters(logger)
    assert "messages" not in c._rates
    assert "messages" not in c._average_rates

    c.do_statistics()
    assert "messages" not in c._rates
    assert "messages" not in c._average_rates

    monkeypatch.setattr("time.time", lambda: 2.0)

    c.do_statistics()
    assert c._rates["messages"] == 0.0
    assert c._average_rates["messages"] == 0.0

    c.count("messages")
    monkeypatch.setattr("time.time", lambda: 3.0)

    c.do_statistics()
    assert c._rates["messages"] == 1.0

    assert pytest.approx(c._average_rates["messages"]) == 0.09999999999999998

    c.count("messages")
    c.count("messages")
    c.count("messages")
    c.count("messages")
    c.count("messages")
    monkeypatch.setattr("time.time", lambda: 4.0)
    c.do_statistics()
    assert c._rates["messages"] == 5.0
    assert pytest.approx(c._average_rates["messages"]) == 0.5899999999999999


def test_perfcounters_columns_match_status_length() -> None:
    c = Perfcounters(logger)
    assert len(c.status_columns()) == len(c.get_status())


def test_perfcounters_column_default_values() -> None:
    c = Perfcounters(logger)
    for column_name, default_value in c.status_columns():
        if column_name.startswith("status_average_") and column_name.endswith("_time"):
            assert isinstance(default_value, float)
            assert default_value == 0.0

        elif column_name.startswith("status_average_") and column_name.endswith("_rate"):
            assert isinstance(default_value, float)
            assert default_value == 0.0

        elif column_name.startswith("status_") and column_name.endswith("_rate"):
            assert isinstance(default_value, float)
            assert default_value == 0.0

        elif column_name.startswith("status_"):
            assert isinstance(default_value, int), "Wrong column type %r: %s" % (
                column_name,
                type(default_value),
            )
            assert default_value == 0, "Wrong column default value %r: %d" % (
                column_name,
                default_value,
            )


def test_perfcounters_correct_status_values() -> None:
    c = Perfcounters(logger)

    for _x in range(5):
        c.count("messages")

    for _x in range(10):
        c.count("events")

    for _x in range(10):
        c.count("connects")

    for _x in range(2):
        c.count("rule_tries")

    for column_name, column_value in zip([n for n, _d in c.status_columns()], c.get_status()):
        if column_name.startswith("status_average_") and column_name.endswith("_time"):
            counter_name = column_name.split("_")[-2]
            assert column_value == c._times.get(counter_name, 0.0)

        elif column_name.startswith("status_average_") and column_name.endswith("_rate"):
            counter_name = column_name.split("_")[-2]
            assert column_value == c._average_rates.get(counter_name, 0.0)

        elif column_name.startswith("status_") and column_name.endswith("_rate"):
            counter_name = column_name.split("_")[-2]
            assert column_value == c._rates.get(counter_name, 0.0)

        elif column_name.startswith("status_"):
            counter_name = "_".join(column_name.split("_")[1:])
            assert column_value == c._counters[counter_name], "Invalid value %r: %r" % (
                column_name,
                c._counters[counter_name],
            )

        else:
            raise NotImplementedError()
