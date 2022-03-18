#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Callable, Sequence, Tuple, Union

import pytest

from cmk.base.api.agent_based.checking_classes import Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.gcp_run import (
    check_gcp_run_cpu,
    check_gcp_run_memory,
    check_gcp_run_network,
    check_gcp_run_requests,
    discover,
    parse_gcp_run,
)
from cmk.base.plugins.agent_based.utils import gcp
from cmk.base.plugins.agent_based.utils.gcp import AssetSection, Section

SECTION_TABLE = [
    [
        '{"metric": {"type": "run.googleapis.com/container/network/received_bytes_count", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"service_name": "aaaa", "project_id": "backup-255820"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/container/network/sent_bytes_count", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"service_name": "aaaa", "project_id": "backup-255820"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"double_value": 79.78333333333333}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"double_value": 797.8333333333334}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/request_count", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"project_id": "backup-255820", "service_name": "aaaa"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"int64_value": "8"}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"int64_value": "0"}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"int64_value": "0"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/container/cpu/allocation_time", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"service_name": "aaaa", "project_id": "backup-255820"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"double_value": 0.10000000000000009}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"double_value": 1.0}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/container/billable_instance_time", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"service_name": "aaaa", "project_id": "backup-255820"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"double_value": 0.001666666666666668}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"double_value": 0.016666666666666666}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"double_value": 0.0}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"double_value": 0.0}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/container/instance_count", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"project_id": "backup-255820", "service_name": "aaaa"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-02-26T09:50:18.962995Z", "end_time": "2022-02-26T09:50:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:49:18.962995Z", "end_time": "2022-02-26T09:49:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:48:18.962995Z", "end_time": "2022-02-26T09:48:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:47:18.962995Z", "end_time": "2022-02-26T09:47:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:46:18.962995Z", "end_time": "2022-02-26T09:46:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:45:18.962995Z", "end_time": "2022-02-26T09:45:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:44:18.962995Z", "end_time": "2022-02-26T09:44:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:43:18.962995Z", "end_time": "2022-02-26T09:43:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:42:18.962995Z", "end_time": "2022-02-26T09:42:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:41:18.962995Z", "end_time": "2022-02-26T09:41:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:39:18.962995Z", "end_time": "2022-02-26T09:39:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:38:18.962995Z", "end_time": "2022-02-26T09:38:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:35:18.962995Z", "end_time": "2022-02-26T09:35:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:34:18.962995Z", "end_time": "2022-02-26T09:34:18.962995Z"}, "value": {"int64_value": "2"}}, {"interval": {"start_time": "2022-02-26T09:33:18.962995Z", "end_time": "2022-02-26T09:33:18.962995Z"}, "value": {"int64_value": "2"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "run.googleapis.com/request_latencies", "labels": {}}, "resource": {"type": "cloud_run_revision", "labels": {"project_id": "backup-255820", "service_name": "aaaa"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-02-26T09:40:18.962995Z", "end_time": "2022-02-26T09:40:18.962995Z"}, "value": {"double_value": 1.99}}, {"interval": {"start_time": "2022-02-26T09:37:18.962995Z", "end_time": "2022-02-26T09:37:18.962995Z"}, "value": {"double_value": 7.719999999999999}}, {"interval": {"start_time": "2022-02-26T09:36:18.962995Z", "end_time": "2022-02-26T09:36:18.962995Z"}, "value": {"double_value": 3.97}}], "unit": ""}'
    ],
]

ASSET_TABLE = [
    ['{"project":"backup-255820"}'],
    [
        '{"name": "//run.googleapis.com/projects/backup-255820/locations/us-central1/services/aaaa", "asset_type": "run.googleapis.com/Service", "resource": {"version": "v1", "discovery_document_uri": "https://run.googleapis.com/$discovery/rest", "discovery_name": "Service", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"metadata": {"name": "aaaa", "generation": 1.0, "uid": "e95937c6-9864-458b-acea-9147be027604", "namespace": "360989076580", "labels": {"cloud.googleapis.com/location": "us-central1"}, "selfLink": "/apis/serving.knative.dev/v1/namespaces/360989076580/services/aaaa", "creationTimestamp": "2022-02-17T14:12:58.71874Z", "annotations": {"run.googleapis.com/ingress-status": "all", "client.knative.dev/user-image": "us-docker.pkg.dev/cloudrun/container/hello", "run.googleapis.com/client-name": "cloud-console", "serving.knative.dev/creator": "max.linke88@gmail.com", "serving.knative.dev/lastModifier": "max.linke88@gmail.com", "run.googleapis.com/ingress": "all"}, "resourceVersion": "AAXYN2StUX8"}, "spec": {"traffic": [{"latestRevision": true, "percent": 100.0}], "template": {"spec": {"serviceAccountName": "360989076580-compute@developer.gserviceaccount.com", "timeoutSeconds": 300.0, "containers": [{"resources": {"limits": {"memory": "512Mi", "cpu": "1000m"}}, "ports": [{"containerPort": 8080.0, "name": "http1"}], "image": "us-docker.pkg.dev/cloudrun/container/hello"}], "containerConcurrency": 80.0}, "metadata": {"name": "aaaa-00001-qax", "annotations": {"autoscaling.knative.dev/maxScale": "4", "run.googleapis.com/client-name": "cloud-console"}}}}, "status": {"url": "https://aaaa-l2ihgnbm5q-uc.a.run.app", "conditions": [{"status": "True", "lastTransitionTime": "2022-02-17T14:15:07.434367Z", "type": "Ready"}, {"type": "ConfigurationsReady", "status": "True", "lastTransitionTime": "2022-02-17T14:15:07.124653Z"}, {"status": "True", "lastTransitionTime": "2022-02-17T14:15:07.434367Z", "type": "RoutesReady"}], "latestReadyRevisionName": "aaaa-00001-qax", "address": {"url": "https://aaaa-l2ihgnbm5q-uc.a.run.app"}, "observedGeneration": 1.0, "latestCreatedRevisionName": "aaaa-00001-qax", "traffic": [{"latestRevision": true, "revisionName": "aaaa-00001-qax", "percent": 100.0}]}, "apiVersion": "serving.knative.dev/v1", "kind": "Service"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-17T14:15:07.434367Z", "org_policy": []}'
    ],
]


def test_parse_gcp():
    section = parse_gcp_run(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    # first row contains general section information and no metrics
    assert n_rows == len(SECTION_TABLE)


@pytest.fixture(name="asset_section")
def fixture_asset_section() -> AssetSection:
    return gcp.parse_assets(ASSET_TABLE)


@pytest.fixture(name="run_services")
def fixture_run_services(asset_section: AssetSection) -> Sequence[Service]:
    return sorted(discover(section_gcp_service_cloud_run=None, section_gcp_assets=asset_section))


def test_no_asset_section_yields_no_service():
    assert len(list(discover(section_gcp_service_cloud_run=None, section_gcp_assets=None))) == 0


def test_discover_two_run_services(run_services: Sequence[Service]):
    assert {b.item for b in run_services} == {"aaaa"}


def test_discover_project_labels(run_services: Sequence[Service]):
    for service in run_services:
        assert ServiceLabel("gcp/projectId", "backup-255820") in service.labels


def test_discover_labels(run_services: Sequence[Service]):
    labels = run_services[0].labels
    assert set(labels) == {
        ServiceLabel("gcp/location", "us-central1"),
        ServiceLabel("gcp/run/name", "aaaa"),
        ServiceLabel("gcp/projectId", "backup-255820"),
    }


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(
        function=check_gcp_run_cpu,
        metrics=[
            "util",
        ],
    ),
    Plugin(
        function=check_gcp_run_memory,
        metrics=[
            "memory_util",
        ],
    ),
    Plugin(
        function=check_gcp_run_network,
        metrics=[
            "net_data_sent",
            "net_data_recv",
        ],
    ),
    Plugin(
        function=check_gcp_run_requests,
        metrics=[
            "faas_total_instance_count",
            "faas_execution_count",
            "faas_execution_times",
            "gcp_billable_time",
        ],
    ),
]
ITEM = "aaaa"


@pytest.fixture(name="section")
def fixture_section() -> Section:
    return parse_gcp_run(SECTION_TABLE)


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request) -> Plugin:
    return request.param


Results = Tuple[Sequence[Union[Metric, Result]], Plugin]


@pytest.fixture(name="results_and_plugin")
def fixture_results(checkplugin: Plugin, section: Section) -> Results:
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM, params=params, section_gcp_service_cloud_run=section, section_gcp_assets=None
        )
    )
    return results, checkplugin


def test_no_run_section_yields_no_metric_data(checkplugin):
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_run=None,
            section_gcp_assets=None,
        )
    )
    assert len(results) == 0


def test_yield_metrics_as_specified(results_and_plugin: Results):
    results, checkplugin = results_and_plugin
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results_and_plugin: Results):
    results, checkplugin = results_and_plugin
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK


class TestConfiguredNotificationLevels:
    # In the example sections we do not have data for all metrics. To be able to test all check plugins
    # use 0, the default value, to check notification levels.
    def test_warn_levels(self, checkplugin: Plugin, section: Section):
        params = {k: (0, None) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM,
                params=params,
                section_gcp_service_cloud_run=section,
                section_gcp_assets=None,
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.WARN

    def test_crit_levels(self, checkplugin: Plugin, section: Section):
        params = {k: (None, 0) for k in checkplugin.metrics}
        results = list(
            checkplugin.function(
                item=ITEM,
                params=params,
                section_gcp_service_cloud_run=section,
                section_gcp_assets=None,
            )
        )
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.CRIT


class TestDefaultMetricValues:
    # requests does not contain example data
    def test_zero_default_if_metric_does_not_exist(self, section):
        params = {k: None for k in ["requests"]}
        results = (
            el
            for el in check_gcp_run_memory(
                item=ITEM,
                params=params,
                section_gcp_service_cloud_run=section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0

    def test_zero_default_if_item_does_not_exist(self, section, checkplugin: Plugin):
        params = {k: None for k in ["requests"]}
        results = (
            el
            for el in checkplugin.function(
                item="no I do not exist",
                params=params,
                section_gcp_service_cloud_run=section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0
