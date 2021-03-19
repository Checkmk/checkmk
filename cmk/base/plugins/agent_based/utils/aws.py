#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
)
from ..agent_based_api.v1.type_defs import (
    DiscoveryResult,
    StringTable,
)
from ..agent_based_api.v1 import Service

GenericAWSSection = Sequence[Mapping[str, Any]]
AWSSectionMetrics = Mapping[str, Mapping[str, Any]]


def parse_aws(string_table: StringTable) -> GenericAWSSection:
    loaded = []
    for row in string_table:
        try:
            loaded.extend(json.loads(" ".join(row)))
        except (TypeError, IndexError):
            pass
    return loaded


def extract_aws_metrics_by_labels(
    expected_metric_names: Iterable[str],
    section: GenericAWSSection,
    extra_keys: Optional[Iterable[str]] = None,
) -> Mapping[str, Dict[str, Any]]:
    if extra_keys is None:
        extra_keys = []
    values_by_labels: Dict[str, Dict[str, Any]] = {}
    for row in section:
        row_id = row['Id'].lower()
        row_label = row['Label']
        row_values = row['Values']
        for expected_metric_name in expected_metric_names:
            expected_metric_name_lower = expected_metric_name.lower()
            if (not row_id.startswith(expected_metric_name_lower) and
                    not row_id.endswith(expected_metric_name_lower)):
                continue

            try:
                # AWSSectionCloudwatch in agent_aws.py yields both the actual values of the metrics
                # as returned by Cloudwatch and the time period over which they were collected (for
                # example 600 s). However, only for metrics based on the "Sum" statistics, the
                # period is not None, because these metrics need to be divided by the period to
                # convert the metric value to a rate. For all other metrics, the time period is
                # None.
                value, time_period = row_values[0]
                if time_period is not None:
                    value /= time_period
            except IndexError:
                continue
            else:
                values_by_labels.setdefault(row_label, {}).setdefault(expected_metric_name, value)
        for extra_key in extra_keys:
            extra_value = row.get(extra_key)
            if extra_value is None:
                continue
            values_by_labels.setdefault(row_label, {}).setdefault(extra_key, extra_value)
    return values_by_labels


def discover_aws_generic(
    section: AWSSectionMetrics,
    required_metrics: Iterable[str],
) -> DiscoveryResult:
    """
    >>> list(discover_aws_generic(
    ... {'x': {'CPUCreditUsage': 0.002455, 'CPUCreditBalance': 43.274031, 'CPUUtilization': 0.033333333}},
    ... ['CPUCreditUsage', 'CPUCreditBalance'],
    ... ))
    [Service(item='x')]
    """
    for instance_name, instance in section.items():
        if all(required_metric in instance for required_metric in required_metrics):
            yield Service(item=instance_name)


def aws_rds_service_item(instance_id: str, region: str) -> str:
    return f'{instance_id} [{region}]'
