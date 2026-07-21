#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
import requests

from cmk.plugins.prometheus.lib import ApiSession, get_api_url
from cmk.plugins.prometheus.special_agents.agent_prometheus import PrometheusAPI, PrometheusServer


def _session_recording_requests(connection: str) -> tuple[ApiSession, list[str]]:
    """Build a real ApiSession (as used in production) whose outgoing request URLs are
    recorded instead of actually sent over the network."""
    requested_urls: list[str] = []
    session = ApiSession(get_api_url(connection, "https"))

    def fake_request(
        _method: str, url: str, params: object = None, verify: object = None
    ) -> requests.models.Response:
        requested_urls.append(url)
        response = requests.models.Response()
        response.status_code = 200
        response._content = json.dumps({"data": {"version": "2.45.0"}}).encode()
        return response

    session._session.request = fake_request  # type: ignore[assignment]
    return session, requested_urls


@pytest.mark.parametrize(
    "connection, expected_base",
    [
        pytest.param(
            "prometheus-server",
            "https://prometheus-server/api/v1/",
            id="plain hostname",
        ),
        pytest.param(
            "prometheus-server:9090",
            "https://prometheus-server:9090/api/v1/",
            id="hostname with port",
        ),
        pytest.param(
            "reverseproxy.example.com/prometheus",
            "https://reverseproxy.example.com/prometheus/api/v1/",
            id="reverse-proxied subpath",
        ),
    ],
)
def test_query_static_endpoint_keeps_connection_subpath(
    connection: str, expected_base: str
) -> None:
    """Regression test: a leading slash in the endpoint passed to query_static_endpoint()
    makes urljoin() discard the whole '/api/v1/' (and any reverse-proxy subpath) from the
    connection's base URL. Endpoints must therefore be relative (no leading slash)."""
    session, requested_urls = _session_recording_requests(connection)
    api_client = PrometheusAPI(session)

    api_client.query_static_endpoint("status/buildinfo")

    assert requested_urls == [expected_base + "status/buildinfo"]


@pytest.mark.parametrize(
    "connection, expected_url",
    [
        pytest.param(
            "prometheus-server",
            "https://prometheus-server/api/v1/status/buildinfo",
            id="plain hostname",
        ),
        pytest.param(
            "reverseproxy.example.com/prometheus",
            "https://reverseproxy.example.com/prometheus/api/v1/status/buildinfo",
            id="reverse-proxied subpath",
        ),
    ],
)
def test_prometheus_version_queries_full_api_path(connection: str, expected_url: str) -> None:
    """End-to-end check of the exact call site that failed for the reported customer issue:
    PrometheusServer._prometheus_version() must hit '.../api/v1/status/buildinfo', not lose
    the connection's subpath."""
    session, requested_urls = _session_recording_requests(connection)
    server = PrometheusServer(PrometheusAPI(session))

    version = server._prometheus_version()

    assert requested_urls == [expected_url]
    assert version == ["2.45.0"]


def test_leading_slash_would_have_dropped_the_subpath() -> None:
    """Documents the bug being fixed: a leading-slash endpoint resolves relative to the
    domain root, silently discarding '/api/v1/' and any reverse-proxy subpath."""
    from urllib.parse import urljoin

    base_url = get_api_url("reverseproxy.example.com/prometheus", "https")
    assert base_url == "https://reverseproxy.example.com/prometheus/api/v1/"

    buggy_url = urljoin(base_url, "/status/buildinfo")
    assert buggy_url == "https://reverseproxy.example.com/status/buildinfo"

    fixed_url = urljoin(base_url, "status/buildinfo")
    assert fixed_url == "https://reverseproxy.example.com/prometheus/api/v1/status/buildinfo"
