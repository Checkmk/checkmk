#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import time_machine
from pytest import MonkeyPatch

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import cadvisor_if

SECTION = {
    "if_out_discards": 0.0,
    "if_out_errors": 0.0,
    "if_out_total": 249.6433876514451,
    "if_in_errors": 0.0,
    "if_in_discards": 0.0,
    "if_in_total": 212.2978367999952,
}


def test_parse_cadvisor_if() -> None:
    assert (
        cadvisor_if.parse_cadvisor_if(
            [
                [
                    '{"if_out_discards": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "0"}], '
                    '"if_out_errors": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "0"}], '
                    '"if_out_total": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "249.6433876514451"}], '
                    '"if_in_errors": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "0"}], '
                    '"if_in_discards": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "0"}], '
                    '"if_in_total": [{"host_selection_label": "pod", "labels": {"pod": "antivirus-5bd5bb8d47-tp87w"}, "value": "212.2978367999952"}]}'
                ]
            ]
        )
        == SECTION
    )


def test_check_cadvisor_if(monkeypatch: MonkeyPatch) -> None:
    vs = {
        "in_bcast.0.Summary.Summary.None": (1000.0, 0),
        "in_disc.0.Summary.Summary.None": (1000.0, 0.0),
        "in_err.0.Summary.Summary.None": (1000.0, 0.0),
        "in_mcast.0.Summary.Summary.None": (1000.0, 0),
        "in_octets.0.Summary.Summary.None": (1000.0, 32.2978367999952),
        "in_ucast.0.Summary.Summary.None": (1000.0, 0),
        "out_bcast.0.Summary.Summary.None": (1000.0, 0),
        "out_disc.0.Summary.Summary.None": (1000.0, 0.0),
        "out_err.0.Summary.Summary.None": (1000.0, 0.0),
        "out_mcast.0.Summary.Summary.None": (1000.0, 0),
        "out_octets.0.Summary.Summary.None": (1000.0, 69.6433876514451),
        "out_ucast.0.Summary.Summary.None": (1000.0, 0),
    }
    monkeypatch.setattr(cadvisor_if, "get_value_store", lambda: vs)

    with time_machine.travel(datetime.datetime.fromtimestamp(1060, tz=ZoneInfo("UTC"))):
        assert list(cadvisor_if.check_cadvisor_if("Summary", SECTION)) == [
            Result(state=State.OK, summary="[0]"),
            Result(state=State.OK, summary="(up)", details="Operational state: up"),
            Result(state=State.OK, summary="In: 3.00 B/s"),
            Metric("in", 3.0, boundaries=(0.0, None)),
            Result(state=State.OK, summary="Out: 3.00 B/s"),
            Metric("out", 3.0, boundaries=(0.0, None)),
            Result(state=State.OK, notice="Errors in: 0 packets/s"),
            Metric("inerr", 0.0),
            Result(state=State.OK, notice="Discards in: 0 packets/s"),
            Metric("indisc", 0.0),
            Result(state=State.OK, notice="Errors out: 0 packets/s"),
            Metric("outerr", 0.0),
            Result(state=State.OK, notice="Discards out: 0 packets/s"),
            Metric("outdisc", 0.0),
        ]
