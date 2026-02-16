#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.kube.agent_based.kube_uptime import _parse_kube_start_time
from cmk.plugins.kube.schemata.api import Timestamp
from cmk.plugins.kube.schemata.section import StartTime
from cmk.plugins.lib.uptime import Section


def test_parse_kube_start_time() -> None:
    assert _parse_kube_start_time(1.0, [['{"start_time": 0}']]) == Section(
        uptime_sec=1.0, message=None
    )


def test_parse_kube_start_time_from_section_model() -> None:
    start_time_json = StartTime(start_time=Timestamp(20)).model_dump_json()
    assert _parse_kube_start_time(100.0, [[start_time_json]]) == Section(
        uptime_sec=80.0, message=None
    )
