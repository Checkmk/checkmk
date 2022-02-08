#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.plugins.metrics.rrd_fetch as rf


def test_needed_elements_of_expression():
    assert set(
        rf.needed_elements_of_expression(
            (
                "transformation",
                ("q90percentile", 95.0),
                [("rrd", "heute", "CPU utilization", "util", "max")],
            )
        )
    ) == {("heute", "CPU utilization", "util", "max")}
