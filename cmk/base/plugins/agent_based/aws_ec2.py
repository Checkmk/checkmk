#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.aws import (
    extract_aws_metrics_by_labels,
    parse_aws,
)

Section = Mapping[str, float]


def parse_aws_ec2(string_table: StringTable) -> Section:
    """
    >>> parse_aws_ec2([[
    ... '[{"Id":', '"id_10_CPUCreditUsage",', '"Label":', '"172.31.41.207-eu-central-1-i-08363bfeff774e12c",',
    ... '"Timestamps":', '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
    ... '"StatusCode":', '"Complete"}]']])
    {'CPUCreditUsage': 0.0030055}
    """
    metrics = extract_aws_metrics_by_labels([
        'CPUCreditUsage',
        'CPUCreditBalance',
        'CPUUtilization',
        'DiskReadOps',
        'DiskWriteOps',
        'DiskReadBytes',
        'DiskWriteBytes',
        'NetworkIn',
        'NetworkOut',
        'StatusCheckFailed_Instance',
        'StatusCheckFailed_System',
    ], parse_aws(string_table))
    # We get exactly one entry: {INST-ID: METRICS}
    # INST-ID is the piggyback host name
    try:
        inst_metrics = list(metrics.values())[-1]
    except IndexError:
        inst_metrics = {}
    return inst_metrics


register.agent_section(
    name="aws_ec2",
    parse_function=parse_aws_ec2,
)
