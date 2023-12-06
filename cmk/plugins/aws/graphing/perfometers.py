#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometer

perfometer_aws_overall_hosts_health_perc = perfometer.Perfometer(
    "aws_overall_hosts_health_perc",
    perfometer.FocusRange(
        perfometer.Closed(0),
        perfometer.Open(10000),
    ),
    ["aws_overall_hosts_health_perc"],
)

perfometer_aws_bucket_size = perfometer.Perfometer(
    "aws_bucket_size",
    perfometer.FocusRange(
        perfometer.Closed(0),
        perfometer.Open(1152921504606846976),
    ),
    ["aws_bucket_size"],
)

perfometer_aws_s3_buckets = perfometer.Perfometer(
    "aws_s3_buckets",
    perfometer.FocusRange(
        perfometer.Closed(0),
        perfometer.Open(2500),
    ),
    ["aws_s3_buckets"],
)
