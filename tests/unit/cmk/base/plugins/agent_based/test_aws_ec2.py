#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.aws_ec2 import check_aws_ec2_network_io


def test_check_aws_ec2_network_io() -> None:
    assert list(check_aws_ec2_network_io("Summary", {}, {"NetworkIn": 1, "NetworkOut": 2,},)) == [
        Result(state=State.OK, summary="[0]"),
        Result(state=State.OK, summary="(up)", details="Operational state: up"),
        Result(state=State.OK, summary="Speed: unknown"),
        Metric("outqlen", 0.0),
        Result(state=State.OK, summary="In: 0.02 B/s"),
        Metric("in", 0.016666666666666666, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Out: 0.03 B/s"),
        Metric("out", 0.03333333333333333, boundaries=(0.0, None)),
        Result(state=State.OK, notice="Errors in: 0 packets/s"),
        Metric("inerr", 0.0),
        Result(state=State.OK, notice="Multicast in: 0 packets/s"),
        Metric("inmcast", 0.0),
        Result(state=State.OK, notice="Broadcast in: 0 packets/s"),
        Metric("inbcast", 0.0),
        Result(state=State.OK, notice="Unicast in: 0 packets/s"),
        Metric("inucast", 0.0),
        Result(state=State.OK, notice="Non-unicast in: 0 packets/s"),
        Metric("innucast", 0.0),
        Result(state=State.OK, notice="Discards in: 0 packets/s"),
        Metric("indisc", 0.0),
        Result(state=State.OK, notice="Errors out: 0 packets/s"),
        Metric("outerr", 0.0),
        Result(state=State.OK, notice="Multicast out: 0 packets/s"),
        Metric("outmcast", 0.0),
        Result(state=State.OK, notice="Broadcast out: 0 packets/s"),
        Metric("outbcast", 0.0),
        Result(state=State.OK, notice="Unicast out: 0 packets/s"),
        Metric("outucast", 0.0),
        Result(state=State.OK, notice="Non-unicast out: 0 packets/s"),
        Metric("outnucast", 0.0),
        Result(state=State.OK, notice="Discards out: 0 packets/s"),
        Metric("outdisc", 0.0),
    ]
