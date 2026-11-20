#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import time
from argparse import Namespace as Args
from collections.abc import Iterator, Mapping

import pytest

from cmk.plugins.aws_v2.special_agent.config import (
    AWSConfig,
    NamingConvention,
    NonEC2PiggybackTemplate,
    Tags,
)
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


# The mypy setup of this test target does not see botocore, so we load it at run time.
ClientError = importlib.import_module("botocore.exceptions").ClientError

QUOTAS = [{"QuotaName": "Clusters per account", "Value": 42.0}]


class FailingQuotaClient:
    def __init__(self, error_code: str) -> None:
        self._error_code = error_code

    def get_paginator(self, operation_name: str) -> FailingQuotaClient:
        assert operation_name == "list_service_quotas"
        return self

    def paginate(
        self,
        ServiceCode: str,  # noqa: ARG002
        PaginationConfig: Mapping[str, object],  # noqa: ARG002
    ) -> Iterator[Mapping[str, object]]:
        raise ClientError(
            {"Error": {"Code": self._error_code, "Message": "nope"}}, "ListServiceQuotas"
        )


def _config() -> AWSConfig:
    return AWSConfig(
        "hostname",
        Args(),
        ([], []),
        NamingConvention.ip_region_instance,
        NonEC2PiggybackTemplate.LONG,
    ).for_account("123456789012")


def test_service_quotas_are_read_from_aws_every_six_hours() -> None:
    client = CountingQuotaClient()
    ServiceQuotas(client, _config(), "region", "ecs").get(use_cache=True)

    cached = ServiceQuotas(client, _config(), "region", "ecs").get(
        use_cache=True, now=time.time() + 5 * 3600
    )

    assert cached == QUOTAS
    assert client.listings == 1


def test_service_quotas_are_read_from_aws_again_after_six_hours() -> None:
    client = CountingQuotaClient()
    ServiceQuotas(client, _config(), "region", "ecs").get(use_cache=True)

    ServiceQuotas(client, _config(), "region", "ecs").get(
        use_cache=True, now=time.time() + 7 * 3600
    )

    assert client.listings == 2


def test_service_quotas_fall_back_to_stored_quotas_when_aws_throttles() -> None:
    ServiceQuotas(CountingQuotaClient(), _config(), "region", "ecs").get(use_cache=True)
    quotas = ServiceQuotas(
        FailingQuotaClient("TooManyRequestsException"), _config(), "region", "ecs"
    )

    stored = quotas.get(use_cache=True, now=time.time() + 6.5 * 3600)

    assert stored == QUOTAS


@pytest.mark.parametrize(
    "error_code, hours, use_cache",
    [
        pytest.param("TooManyRequestsException", 13, True, id="stored quotas too old"),
        pytest.param("AccessDeniedException", 6.5, True, id="not throttled"),
        pytest.param("TooManyRequestsException", 6.5, False, id="cache disabled"),
    ],
)
def test_service_quotas_report_the_aws_error(
    error_code: str, hours: float, use_cache: bool
) -> None:
    ServiceQuotas(CountingQuotaClient(), _config(), "region", "ecs").get(use_cache=True)
    quotas = ServiceQuotas(FailingQuotaClient(error_code), _config(), "region", "ecs")

    with pytest.raises(ClientError):
        quotas.get(use_cache=use_cache, now=time.time() + hours * 3600)
