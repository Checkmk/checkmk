#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.plugins.agent_based.gcp_gce import parse_gce_uptime
from cmk.base.plugins.agent_based.utils import uptime


def test_parse_piggy_back():
    uptime_section = parse_gce_uptime(
        [
            [
                '{"metric": {"type": "compute.googleapis.com/instance/uptime_total", "labels": {}}, "resource": {"type": "gce_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "4916403162284897775"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-05-05T13:55:15.478132Z", "end_time": "2022-05-05T13:55:15.478132Z"}, "value": {"int64_value": "10"}}], "unit": ""}'
            ],
        ]
    )
    assert uptime_section == uptime.Section(uptime_sec=10, message=None)
