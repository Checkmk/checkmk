#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_aws_wafv2_allowed_requests_rate = metrics.Metric(
    name="aws_wafv2_allowed_requests_rate",
    title=Title("Avg. rate of allowed requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_wafv2_blocked_requests_rate = metrics.Metric(
    name="aws_wafv2_blocked_requests_rate",
    title=Title("Avg. rate of blocked requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_aws_wafv2_requests_rate = metrics.Metric(
    name="aws_wafv2_requests_rate",
    title=Title("Avg. request rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)

graph_aws_wafv2_web_acl_requests = graphs.Graph(
    name="aws_wafv2_web_acl_requests",
    title=Title("Web ACL Requests"),
    compound_lines=[
        "aws_wafv2_allowed_requests_rate",
        "aws_wafv2_blocked_requests_rate",
    ],
    simple_lines=["aws_wafv2_requests_rate"],
)
