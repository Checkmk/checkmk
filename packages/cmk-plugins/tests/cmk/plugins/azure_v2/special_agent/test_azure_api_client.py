#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from typing import Literal

import pytest

from cmk.plugins.azure_v2.special_agent.azure_api_client import (
    ApiError,
    ApiErrorAuthorizationRequestDenied,
    BaseAsyncApiClient,
    get_graph_authority_urls,
    get_mgmt_authority_urls,
    HTTPProxyConfig,
    to_requests_proxies,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param("NO_PROXY", {"http": "", "https": ""}, id="no proxy"),
        pytest.param("FROM_ENVIRONMENT", {}, id="proxy from environment"),
        pytest.param(
            "http://proxy:3128",
            {"http": "http://proxy:3128", "https": "http://proxy:3128"},
            id="explicit proxy",
        ),
    ],
)
def test_proxy_setting_becomes_proxies_per_scheme(raw: str, expected: HTTPProxyConfig) -> None:
    assert to_requests_proxies(raw) == expected


@pytest.mark.parametrize(
    "authority, expected",
    [
        pytest.param(
            "global",
            (
                "https://login.microsoftonline.com",
                "https://graph.microsoft.com",
                "https://graph.microsoft.com/v1.0/",
            ),
            id="global",
        ),
        pytest.param(
            "china",
            (
                "https://login.partner.microsoftonline.cn",
                "https://microsoftgraph.chinacloudapi.cn",
                "https://microsoftgraph.chinacloudapi.cn/v1.0/",
            ),
            id="china",
        ),
    ],
)
def test_graph_urls_match_the_cloud(
    authority: Literal["global", "china"], expected: tuple[str, str, str]
) -> None:
    urls = get_graph_authority_urls(authority)

    assert (urls.login, urls.resource, urls.base) == expected


@pytest.mark.parametrize(
    "authority, expected",
    [
        pytest.param(
            "global",
            (
                "https://login.microsoftonline.com",
                "https://management.azure.com",
                "https://management.azure.com/subscriptions/sub/",
            ),
            id="global",
        ),
        pytest.param(
            "china",
            (
                "https://login.partner.microsoftonline.cn",
                "https://management.chinacloudapi.cn",
                "https://management.chinacloudapi.cn/subscriptions/sub/",
            ),
            id="china",
        ),
    ],
)
def test_management_urls_match_the_cloud(
    authority: Literal["global", "china"], expected: tuple[str, str, str]
) -> None:
    urls = get_mgmt_authority_urls(authority, "sub")

    assert (urls.login, urls.resource, urls.base) == expected


def test_unknown_cloud_is_rejected_for_graph() -> None:
    with pytest.raises(ValueError, match="Unknown authority"):
        get_graph_authority_urls("mars")  # type: ignore[arg-type]


def test_unknown_cloud_is_rejected_for_management() -> None:
    with pytest.raises(ValueError, match="Unknown authority"):
        get_mgmt_authority_urls("mars", "sub")  # type: ignore[arg-type]


def _mgmt_client(authority: Literal["global", "china"]) -> BaseAsyncApiClient:
    return BaseAsyncApiClient(
        get_mgmt_authority_urls(authority, "sub"), {}, "tenant", "client", "secret"
    )


def _graph_client() -> BaseAsyncApiClient:
    return BaseAsyncApiClient(get_graph_authority_urls("global"), {}, "tenant", "client", "secret")


def test_regional_metrics_url_points_to_the_region() -> None:
    client = _mgmt_client("global")

    assert (
        client.build_regional_url("westeurope", "/metrics:getBatch")
        == "https://westeurope.metrics.monitor.azure.com/subscriptions/sub/metrics:getBatch"
    )


def test_graph_client_has_no_regional_url() -> None:
    client = _graph_client()

    with pytest.raises(ValueError, match="Regional URL not configured"):
        client.build_regional_url("westeurope", "metrics:getBatch")


def test_client_reports_no_rate_limit_before_any_request() -> None:
    assert _graph_client().ratelimit is None


def test_lookup_returns_the_value_of_the_key() -> None:
    assert BaseAsyncApiClient.lookup_json_data({"value": [1, 2]}, "value") == [1, 2]


@pytest.mark.parametrize(
    "answer, expected_type, expected_message",
    [
        pytest.param(
            {"code": "Authorization_RequestDenied", "message": "Insufficient privileges"},
            ApiErrorAuthorizationRequestDenied,
            "Insufficient privileges",
            id="denied authorization",
        ),
        pytest.param(
            {"code": "ResourceNotFound", "message": "No such resource"},
            ApiError,
            "No such resource",
            id="error with code and message",
        ),
        pytest.param(
            {"unexpected": "answer"},
            ApiError,
            "unexpected",
            id="answer of unknown shape",
        ),
    ],
)
def test_answer_without_the_key_raises_the_matching_error(
    answer: dict[str, str], expected_type: type[ApiError], expected_message: str
) -> None:
    with pytest.raises(expected_type, match=expected_message) as error:
        BaseAsyncApiClient.lookup_json_data(answer, "value")

    assert type(error.value) is expected_type
