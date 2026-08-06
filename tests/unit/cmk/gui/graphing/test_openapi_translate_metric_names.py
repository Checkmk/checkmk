#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The fetcher stand-ins are constructed with the endpoint's keyword arguments, which only
# Callable[..., ...] can spell; the sibling endpoint test does the same.
# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Mapping

import pytest

from cmk.graphing_engine import HostName, MetricName, Service, ServiceName
from cmk.gui.graphing.openapi import translate_metric_names as endpoint_module
from cmk.livestatus_client import MKLivestatusSocketError
from tests.testlib.rest_api_client import ClientRegistry

# The CPU utilization check reports the raw perf-data name "wait", which the collection
# plug-in renames to the metric "io_wait".
_RAW_NAME = MetricName("wait")
_CANONICAL_NAME = MetricName("io_wait")


def _fetcher_returning(
    mapping: Mapping[Service, Mapping[MetricName, MetricName]],
    asked_about: dict[str, object],
) -> Callable[..., Callable[[], Mapping[Service, Mapping[MetricName, MetricName]]]]:
    """Stand in for RRDFetchMetricNameMapping, recording the service it was asked about."""

    def _make(**kwargs: object) -> Callable[[], Mapping[Service, Mapping[MetricName, MetricName]]]:
        asked_about.update(kwargs)
        return lambda: mapping

    return _make


def test_translate_metric_names_returns_the_fetched_mapping(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked_about: dict[str, object] = {}
    monkeypatch.setattr(
        endpoint_module,
        "RRDFetchMetricNameMapping",
        _fetcher_returning(
            {
                Service(
                    host_name=HostName("my-host"),
                    service_name=ServiceName("CPU utilization"),
                ): {_RAW_NAME: _CANONICAL_NAME}
            },
            asked_about,
        ),
    )

    resp = clients.Graph.translate_metric_names(
        hostname="my-host", service_description="CPU utilization"
    )

    assert resp.json["metric_names"] == {"wait": "io_wait"}
    # The mapping has to be the one for the posted service, not for whatever the fetcher was
    # handed: without this the endpoint could ignore the request body and still pass.
    assert asked_about["host_name"] == "my-host"
    assert asked_about["service_name"] == "CPU utilization"


def test_translate_metric_names_of_an_unknown_service_is_an_empty_mapping(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An unmonitored host or service resolves to no rows. That is an empty answer, not an error:
    # the caller is the one that turns it into a message.
    monkeypatch.setattr(endpoint_module, "RRDFetchMetricNameMapping", _fetcher_returning({}, {}))

    resp = clients.Graph.translate_metric_names(
        hostname="my-host", service_description="No such service"
    )

    assert resp.json["metric_names"] == {}


def test_translate_metric_names_scopes_the_fetch_to_a_site_the_user_may_see(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked_about: dict[str, object] = {}
    monkeypatch.setattr(
        endpoint_module, "RRDFetchMetricNameMapping", _fetcher_returning({}, asked_about)
    )

    clients.Graph.translate_metric_names(
        hostname="my-host", service_description="CPU utilization", site="NO_SITE"
    )

    assert asked_about["site_id"] == "NO_SITE"


def test_translate_metric_names_of_a_site_the_user_may_not_see_is_rejected(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A site outside the user's list would otherwise scope the query to nothing and answer 200 with
    # an empty mapping, which reads exactly like a service that has no perf data.
    monkeypatch.setattr(endpoint_module, "RRDFetchMetricNameMapping", _fetcher_returning({}, {}))

    resp = clients.Graph.translate_metric_names(
        hostname="my-host",
        service_description="CPU utilization",
        site="no-such-site",
        expect_ok=False,
    )

    assert resp.status_code == 400


def test_translate_metric_names_livestatus_failure_is_503(
    clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(
        **_kwargs: object,
    ) -> Callable[[], Mapping[Service, Mapping[MetricName, MetricName]]]:
        def _fetch() -> Mapping[Service, Mapping[MetricName, MetricName]]:
            raise MKLivestatusSocketError("connection refused")

        return _fetch

    monkeypatch.setattr(endpoint_module, "RRDFetchMetricNameMapping", _raise)

    resp = clients.Graph.translate_metric_names(
        hostname="my-host", service_description="CPU utilization", expect_ok=False
    )

    assert resp.status_code == 503
    assert "connection refused" in resp.json["detail"]
