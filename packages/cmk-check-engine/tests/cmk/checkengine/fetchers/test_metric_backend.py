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
    assert config.host_name == "my-host"
    assert len(config.attribute_filter_groups) == 1
    group = config.attribute_filter_groups[0]
    assert group.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]
    assert group.host_name_template is None


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
    # The template is carried through verbatim on the single group and resolved by the telemetry
    # fetcher; the config does not add any derived filter itself.
    assert len(config.attribute_filter_groups) == 1
    group = config.attribute_filter_groups[0]
    assert group.host_name_template == "deployment_$RESOURCE_ATTR.k8s.deployment.name$"
    assert group.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]


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
    assert len(config.attribute_filter_groups) == 1
    group = config.attribute_filter_groups[0]
    assert group.host_name_template == "$RESOURCE_ATTR.service.name$"
    assert group.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]


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
    assert len(config.attribute_filter_groups) == 1
    assert config.attribute_filter_groups[0].host_name_template == "$SCOPE_ATTR.scope.name$"


def test_from_serialized_reads_attribute_filter_groups_union() -> None:
    # Hosts produced by multiple DCD rules carry the union of the rules' filters as groups. The
    # resolved filters are stored directly, so the groups carry no host name template.
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps(
            {
                "attribute_filters": _FILTERS,
                "attribute_filter_groups": [
                    _FILTERS,
                    {
                        "resource_attributes": [{"key": "k8s.pod.name", "value": "pod-1"}],
                        "scope_attributes": [],
                        "data_point_attributes": [],
                    },
                ],
            }
        ),
        check_interval=60.0,
        host_name="my-host",
    )
    assert [g.resource_attribute_filters for g in config.attribute_filter_groups] == [
        [AttributeFilter(key="team", value="infra")],
        [AttributeFilter(key="k8s.pod.name", value="pod-1")],
    ]
    assert all(g.host_name_template is None for g in config.attribute_filter_groups)
