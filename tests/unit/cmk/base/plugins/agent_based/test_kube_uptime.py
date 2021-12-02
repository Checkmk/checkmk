#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from freezegun import freeze_time

from cmk.base.plugins.agent_based.kube_uptime import parse_k8s_start_time
from cmk.base.plugins.agent_based.utils.uptime import Section


@freeze_time("1970-01-01 00:00:01")
def test_parse_k8s_start_time() -> None:
    assert parse_k8s_start_time([['{"start_time": 0}']]) == Section(uptime_sec=1.0, message=None)
