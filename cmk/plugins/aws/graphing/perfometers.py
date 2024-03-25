#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometers

perfometer_aws_overall_hosts_health_perc = perfometers.Perfometer(
    name="aws_overall_hosts_health_perc",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
    segments=["aws_overall_hosts_health_perc"],
)

perfometer_aws_bucket_size = perfometers.Perfometer(
    name="aws_bucket_size",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(2000000000)),
    segments=["aws_bucket_size"],
)

perfometer_aws_s3_buckets = perfometers.Perfometer(
    name="aws_s3_buckets",
    focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(90)),
    segments=["aws_s3_buckets"],
)
