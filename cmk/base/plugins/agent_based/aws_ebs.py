#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.aws import extract_aws_metrics_by_labels, parse_aws

Section = Mapping[str, Mapping[str, float]]


def parse_aws_ebs(string_table: StringTable) -> Section:
    """
    >>> parse_aws_ebs([[
    ... '[{"Id":', '"id_10_VolumeReadOps",', '"Label":', '"123",',
    ... '"Timestamps":', '["2020-12-01', '12:24:00+00:00"],', '"Values":', '[[0.0030055,', 'null]],',
    ... '"StatusCode":', '"Complete"}]']])
    {'123': {'VolumeReadOps': 0.0030055}}
    """
    return extract_aws_metrics_by_labels(
        [
            "VolumeReadOps",
            "VolumeWriteOps",
            "VolumeReadBytes",
            "VolumeWriteBytes",
            "VolumeQueueLength",
            "BurstBalance",
            # "VolumeThroughputPercentage",
            # "VolumeConsumedReadWriteOps",
            # "VolumeTotalReadTime",
            # "VolumeTotalWriteTime",
            # "VolumeIdleTime",
        ],
        parse_aws(string_table),
    )


register.agent_section(
    name="aws_ebs",
    parse_function=parse_aws_ebs,
)
