#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.statgrab_load import parse_statgrab_load
from cmk.base.plugins.agent_based.utils.cpu import Load, Section


def test_parse_statgrab_load() -> None:
    assert parse_statgrab_load(
        [
            ["min1", "2.500000"],
            ["min15", "5.898438"],
            ["min5", "4.191406"],
        ]
    ) == Section(
        load=Load(
            load1=2.500000,
            load5=4.191406,
            load15=5.898438,
        ),
        num_cpus=1,
    )
