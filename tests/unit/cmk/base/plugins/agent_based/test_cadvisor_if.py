#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.cadvisor_if import check_cadvisor_if, parse_cadvisor_if

SECTION = {
    "if_out_discards": 0.0,
    "if_out_errors": 0.0,
    "if_out_total": 249.6433876514451,
    "if_in_errors": 0.0,
    "if_in_discards": 0.0,
    "if_in_total": 212.2978367999952,
}


def test_parse_cadvisor_if():
    assert (
        parse_cadvisor_if(
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


def test_check_cadvisor_if():
    # first run: initialize counters
    list(check_cadvisor_if("Summary", SECTION))
    assert list(check_cadvisor_if("Summary", SECTION)) == [
        Result(state=State.OK, summary="[0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="In: 0.00 B/s"),
        Metric("in", 0.0, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 0.00 B/s"),
        Metric("out", 0.0, boundaries=(0.0, None)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]
