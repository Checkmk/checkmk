#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Iterable, Mapping, Sequence

import pytest

from cmk.special_agents.agent_aws import AWSConfig, AWSRegionLimit, SNSLimits

from .agent_aws_fake_clients import SNSListSubscriptionsIB, SNSListTopicsIB


class PaginatorTopics:
    def __init__(self, topics: Sequence[Mapping]) -> None:
        self._topics = topics

    def paginate(self) -> Iterable[Mapping]:
        yield {
            "Topics": self._topics,
        }


class PaginatorSubscriptions:
    def __init__(self, subscriptions: Sequence[Mapping]) -> None:
        self._subscriptions = subscriptions

    def paginate(self) -> Iterable[Mapping]:
        yield {
            "Subscriptions": self._subscriptions,
        }


class FakeSNSClient:
    def __init__(self, n_std_topics: int, n_fifo_topics: int, n_subs: int) -> None:
        self._topics = SNSListTopicsIB.create_instances(amount=n_std_topics + n_fifo_topics)
        for idx in range(n_fifo_topics):
            self._topics[-(idx + 1)]["TopicArn"] += ".fifo"
        self._subscriptions = SNSListSubscriptionsIB.create_instances(amount=n_subs)

    def get_paginator(self, operation_name):
        if operation_name == "list_topics":
            return PaginatorTopics(self._topics)
        if operation_name == "list_subscriptions":
            return PaginatorSubscriptions(self._subscriptions)
        raise NotImplementedError


def _create_sns_limits(n_std_topics: int, n_fifo_topics: int, n_subs: int) -> SNSLimits:
    return SNSLimits(
        client=FakeSNSClient(n_std_topics, n_fifo_topics, n_subs),
        region="region",
        config=AWSConfig("hostname", [], (None, None)),
    )


@pytest.mark.parametrize(
    ["n_std_topics", "n_fifo_topics", "n_subs"],
    [pytest.param(0, 0, 0, id="no sns services"), pytest.param(3, 3, 3, id="some sns data")],
)
def test_agent_aws_sns_limits(n_std_topics: int, n_fifo_topics: int, n_subs: int) -> None:
    sns_limits = _create_sns_limits(n_std_topics, n_fifo_topics, n_subs)
    sns_limits_results = sns_limits.run().results

    assert sns_limits.cache_interval == 300
    assert sns_limits.period == 600
    assert sns_limits.name == "sns_limits"
    limits_topics_standard: AWSRegionLimit = sns_limits_results[0].content[0]
    limits_topics_fifo: AWSRegionLimit = sns_limits_results[0].content[1]
    assert limits_topics_standard.amount == n_std_topics
    assert limits_topics_fifo.amount == n_fifo_topics
