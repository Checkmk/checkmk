#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import perfometer

perfometer_aws_overall_hosts_health_perc = perfometer.Perfometer(
    name="aws_overall_hosts_health_perc",
    focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
    segments=["aws_overall_hosts_health_perc"],
)

perfometer_aws_bucket_size = perfometer.Perfometer(
    name="aws_bucket_size",
    focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Open(12148001999)),
    segments=["aws_bucket_size"],
)

perfometer_aws_s3_buckets = perfometer.Perfometer(
    name="aws_s3_buckets",
    focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Open(565)),
    segments=["aws_s3_buckets"],
)
