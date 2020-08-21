#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.ac_tests import ACTestGenericCheckHelperUsage


def test_local_connection_mocked(mock_livestatus):
    live = mock_livestatus
    live.expect_query('GET status\nColumns: helper_usage_generic average_latency_generic\n')
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute()
        list(gen)
