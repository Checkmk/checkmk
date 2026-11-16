#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace as Args
from collections.abc import Iterator, Mapping

import pytest

from cmk.plugins.aws_v2.special_agent.config import AWSConfig, NamingConvention, Tags
from cmk.plugins.aws_v2.special_agent.sections.core import (
    filter_resources_matching_tags,
    ServiceQuotas,
)


@pytest.mark.parametrize(
    "resource_tags, tags_to_match, expected_result",
    [
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "no-match-value"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [{"Key": "tag-key", "Value": "match-value"}],
            {"ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
            },
            [{"Key": "tag-key", "Value": "match-value"}],
            set(),
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "no-match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "match-value2"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": "match-value"}],
                "ARN2": [
                    {"Key": "tag-key2", "Value": "match-value2"},
                    {"Key": "tag-key", "Value": "match-value"},
                ],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
                {"Key": "tag-key2", "Value": "match-value2"},
            ],
            {"ARN1", "ARN2"},
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": ""}],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            {
                "ARN1": [],
            },
            [
                {"Key": "tag-key", "Value": "match-value"},
            ],
            set(),
        ),
        (
            {
                "ARN1": [],
            },
            [],
            set(),
        ),
        (
            {
                "ARN1": [{"Key": "tag-key", "Value": ""}],
            },
            [],
            set(),
        ),
    ],
)
def test_filter_resources_matching_tags(
    resource_tags: dict[str, Tags],
    tags_to_match: Tags,
    expected_result: set[str],
) -> None:
    assert filter_resources_matching_tags(resource_tags, tags_to_match) == expected_result


class CountingQuotaClient:
    def __init__(self) -> None:
        self.listings = 0

    def get_paginator(self, operation_name: str) -> CountingQuotaClient:
        assert operation_name == "list_service_quotas"
        return self

    def paginate(
        self,
        ServiceCode: str,  # noqa: ARG002
        PaginationConfig: Mapping[str, object],  # noqa: ARG002
    ) -> Iterator[Mapping[str, object]]:
        self.listings += 1
        yield {"Quotas": [{"QuotaName": "Clusters per account", "Value": 42.0}]}


def test_service_quotas_are_read_from_aws_once_a_day() -> None:
    config = AWSConfig(
        "hostname", Args(), ([], []), NamingConvention.ip_region_instance
    ).for_account("123456789012")
    client = CountingQuotaClient()
    ServiceQuotas(client, config, "region", "ecs").get_data(use_cache=True)
    quotas = ServiceQuotas(client, config, "region", "ecs")

    cached = quotas.get_data(use_cache=True)

    assert cached == [{"QuotaName": "Clusters per account", "Value": 42.0}]
    assert client.listings == 1
    assert quotas.cache_interval == 24 * 3600
