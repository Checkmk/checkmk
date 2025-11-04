#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Any

import pytest

from cmk.plugins.aws.lib import extract_aws_metrics_by_labels, GenericAWSSection


@pytest.mark.parametrize(
    ["metric_names", "section", "expected_output"],
    [
        pytest.param(
            ["VolumeWriteBytes"],
            [
                {
                    "Id": "id_0_CPUUtilization",
                    "Label": "test-redis-cluster-1-0001-001",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[3.550924784186728, None]],
                },
            ],
            {},
            id="no match",
        ),
        pytest.param(
            ["CPUUtilization", "EngineCPUUtilization"],
            [
                {
                    "Id": "id_0_CPUUtilization",
                    "Label": "test-redis-cluster-1-0001-001",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[3.550924784186728, None]],
                },
                {
                    "Id": "id_0_EngineCPUUtilization",
                    "Label": "test-redis-cluster-1-0001-001",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[0.28168917995511694, None]],
                },
            ],
            {
                "test-redis-cluster-1-0001-001": {
                    "CPUUtilization": 3.550924784186728,
                    "EngineCPUUtilization": 0.28168917995511694,
                }
            },
            id="metric name contained in another metric",
        ),
        pytest.param(
            ["HTTPCode_ELB_3XX_Count"],
            [
                {
                    "Id": "id_0_HTTPCode_ELB_3XX_Count",
                    "Label": "test-redis-cluster-1-0001-001",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[572.0, None]],
                },
            ],
            {
                "test-redis-cluster-1-0001-001": {
                    "HTTPCode_ELB_3XX_Count": 572.0,
                }
            },
            id="metric name with underscores",
        ),
        pytest.param(
            ["RequestCount"],
            [
                {
                    "Id": "id_0_consul_port_80_RequestCount",
                    "Label": "consul-port-80",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[1177.0, None]],
                },
            ],
            {
                "consul-port-80": {
                    "RequestCount": 1177.0,
                }
            },
            id="id with additional args",
        ),
        pytest.param(
            ["HTTPCode_Target_4XX_Count"],
            [
                {
                    "Id": "id_0_consul_port_80_HTTPCode_Target_4XX_Count",
                    "Label": "consul-port-80",
                    "StatusCode": "Complete",
                    "Timestamps": ["2023-01-03 09:47:00+00:00"],
                    "Values": [[582.0, None]],
                },
            ],
            {
                "consul-port-80": {
                    "HTTPCode_Target_4XX_Count": 582.0,
                }
            },
            id="id with additional args and metric name with underscores",
        ),
    ],
)
def test_extract_aws_metrics_by_labels(
    metric_names: Iterable[str],
    section: GenericAWSSection,
    expected_output: Mapping[str, dict[str, Any]],
) -> None:
    result = extract_aws_metrics_by_labels(metric_names, section)

    assert result == expected_output
