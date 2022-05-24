#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based import aws_sns_limits
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


def test_discover() -> None:
    assert list(
        aws_sns_limits.discover(
            section={
                "eu-central-1": [
                    ["topics_standard", "Standard Topics Limit", 100000, 2, str],
                    ["topics_fifo", "FIFO Topics Limit", 1000, 1, str],
                ]
            }
        )
    ) == [Service(item="eu-central-1")]


def test_check() -> None:
    assert list(
        aws_sns_limits.check(
            item="eu-central-1",
            params={
                "subscriptions": (None, 80.0, 90.0),
                "topics_fifo": (None, 80.0, 90.0),
                "topics_standard": (None, 80.0, 90.0),
            },
            section={
                "eu-central-1": [
                    ["topics_standard", "Standard Topics Limit", 100000, 2, str],
                    ["topics_fifo", "FIFO Topics Limit", 1000, 1, str],
                ]
            },
        )
    ) == [
        Metric("aws_sns_topics_standard", 2.0),
        Result(state=State.OK, notice="Standard Topics Limit: 2 (of max. 100000), <0.01%"),
        Metric("aws_sns_topics_fifo", 1.0),
        Result(state=State.OK, notice="FIFO Topics Limit: 1 (of max. 1000), 0.10%"),
    ]
