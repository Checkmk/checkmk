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


def test_from_serialized_without_host_name_key_uses_filters_only() -> None:
    config = MetricBackendFetcherConfig.from_serialized(
        json.dumps({"attribute_filters": _FILTERS}),
        check_interval=60.0,
        host_name="my-host",
    )
    assert config.resource_attribute_filters == [AttributeFilter(key="team", value="infra")]


def test_from_serialized_expands_host_name_key_into_resource_filter() -> None:
    # Manual host: the single key is expanded into a resource filter matching the host name,
    # in addition to any configured filters.
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
    assert config.resource_attribute_filters == [
        AttributeFilter(key="service.name", value="my-host"),
        AttributeFilter(key="team", value="infra"),
    ]
