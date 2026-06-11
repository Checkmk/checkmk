#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.checkengine.fetchers.metric_backend import AttributeFilter, MetricBackendFetcherConfig

_FILTERS = {
    "resource_attributes": [{"key": "team", "value": "infra"}],
    "scope_attributes": [],
    "data_point_attributes": [],
}


def test_from_serialized_carries_configured_filters_only() -> None:
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps({"attribute_filters": _FILTERS}),
        check_interval=60.0,
        host_name="my-host",
    )
    assert config.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]
    assert config.host_name == "my-host"
    assert config.host_name_template is None


def test_from_serialized_reads_host_name_template() -> None:
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps(
            {
                "attribute_filters": _FILTERS,
                "host_name_template": "deployment_$RESOURCE_ATTR.k8s.deployment.name$",
            }
        ),
        check_interval=60.0,
        host_name="my-host",
    )
    # The template is carried through verbatim and resolved by the telemetry fetcher; the config
    # does not add any derived filter itself.
    assert config.host_name_template == "deployment_$RESOURCE_ATTR.k8s.deployment.name$"
    assert config.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]


def test_from_serialized_maps_legacy_single_key_to_template() -> None:
    # Backward compatibility: a host configured before the template feature carries a single
    # resource attribute key, which maps to the equivalent template.
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps(
            {
                "attribute_filters": _FILTERS,
                "host_name_resource_attribute_key": "service.name",
            }
        ),
        check_interval=60.0,
        host_name="my-host",
    )
    assert config.host_name_template == "$RESOURCE_ATTR.service.name$"
    assert config.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]


def test_from_serialized_prefers_template_over_legacy_key() -> None:
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps(
            {
                "attribute_filters": _FILTERS,
                "host_name_template": "$SCOPE_ATTR.scope.name$",
                "host_name_resource_attribute_key": "service.name",
            }
        ),
        check_interval=60.0,
        host_name="my-host",
    )
    assert config.host_name_template == "$SCOPE_ATTR.scope.name$"
