#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.aws.agent_based.aws_elb import check_aws_elb_statistics


def test_check_aws_elb_statistics() -> None:
    section = {
        "RequestCount": 693.235,
        "SurgeQueueLength": 1024.0,
        "SpilloverCount": 0.058333333333333334,
        "Latency": 4.2748083637903225e-06,
        "HealthyHostCount": 1.8,
        "UnHealthyHostCount": 0.0,
        "BackendConnectionErrors": 0.058333333333333334,
    }
    assert list(check_aws_elb_statistics({}, section)) == [
        Result(state=State.OK, summary="Surge queue length: 1024"),
        Metric("aws_surge_queue_length", 1024.0),
        Result(state=State.OK, summary="Spillover: 0.058/s"),
        Metric("aws_spillover", 0.058333333333333334),
    ]
