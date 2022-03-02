#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import register, render
from .agent_based_api.v1.type_defs import CheckResult, StringTable
from .utils import gcp


def parse_gcp_gcs(string_table: StringTable) -> gcp.Section:
    return gcp.parse_gcp(string_table, "bucket_name")


register.agent_section(name="gcp_service_gcs", parse_function=parse_gcp_gcs)

discover = gcp.discover


def check_gcp_gcs_requests(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {"requests": gcp.MetricSpec("storage.googleapis.com/api/request_count", str)}
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_requests",
    sections=["gcp_service_gcs"],
    service_name="GCP GCS requests %s",
    check_ruleset_name="gcp_gcs_requests",
    discovery_function=discover,
    check_function=check_gcp_gcs_requests,
    check_default_parameters={},
)


def check_gcp_gcs_network(
    item: str, params: Mapping[str, Any], section: gcp.Section
) -> CheckResult:
    metrics = {
        "net_data_sent": gcp.MetricSpec(
            "storage.googleapis.com/network/sent_bytes_count", render.bytes
        ),
        "net_data_recv": gcp.MetricSpec(
            "storage.googleapis.com/network/received_bytes_count", render.bytes
        ),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_network",
    sections=["gcp_service_gcs"],
    service_name="GCP GCS networks %s",
    check_ruleset_name="gcp_gcs_network",
    discovery_function=discover,
    check_function=check_gcp_gcs_network,
    check_default_parameters={},
)


def check_gcp_gcs_object(item: str, params: Mapping[str, Any], section: gcp.Section) -> CheckResult:
    metrics = {
        "aws_bucket_size": gcp.MetricSpec(
            "storage.googleapis.com/storage/total_bytes", render.bytes
        ),
        "aws_num_objects": gcp.MetricSpec("storage.googleapis.com/storage/object_count", str),
    }
    timeseries = section[item].rows
    yield from gcp.generic_check(metrics, timeseries, params)


register.check_plugin(
    name="gcp_gcs_objects",
    sections=["gcp_service_gcs"],
    service_name="GCP GCS objects %s",
    check_ruleset_name="gcp_gcs_objects",
    discovery_function=discover,
    check_function=check_gcp_gcs_object,
    check_default_parameters={},
)
