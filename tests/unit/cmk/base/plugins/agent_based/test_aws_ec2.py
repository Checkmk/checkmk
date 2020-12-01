#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters
from cmk.base.plugins.agent_based.aws_ec2 import check_aws_ec2_network_io


def test_check_aws_ec2_network_io():
    assert list(
        check_aws_ec2_network_io(
            "Summary",
            Parameters({}),
            {
                "NetworkIn": 1,
                "NetworkOut": 2,
            },
        )) == [
            Result(state=State.OK, summary='[0]'),
            Result(state=State.OK, summary='(up)', details='Operational state: up'),
            Result(state=State.OK, summary='Speed: unknown'),
            Metric('in', 0.016666666666666666, boundaries=(0.0, None)),
            Metric('inmcast', 0.0),
            Metric('inbcast', 0.0),
            Metric('inucast', 0.0),
            Metric('innucast', 0.0),
            Metric('indisc', 0.0),
            Metric('inerr', 0.0),
            Metric('out', 0.03333333333333333, boundaries=(0.0, None)),
            Metric('outmcast', 0.0),
            Metric('outbcast', 0.0),
            Metric('outucast', 0.0),
            Metric('outnucast', 0.0),
            Metric('outdisc', 0.0),
            Metric('outerr', 0.0),
            Metric('outqlen', 0.0),
            Result(state=State.OK, summary='In: 0.02 B/s'),
            Result(state=State.OK, summary='Out: 0.03 B/s'),
        ]
