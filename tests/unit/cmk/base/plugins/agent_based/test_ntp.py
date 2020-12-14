#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.utils.type_defs import CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.ntp import check_ntp, check_ntp_summary, _ntp_fmt_time, Peer, Section
from cmk.base.api.agent_based import value_store


def test_check_ntp():
    section: Section = {
        '42.202.61.100': Peer("-", "42.202.61.100", ".INIT.", 16, _ntp_fmt_time("-"), "0", 0.0, 0.0)
    }
    with value_store.context(CheckPluginName("ntp"), None):
        assert list(check_ntp("item", {}, section)) == []


def test_check_ntp_summanry():
    section: Section = {}
    with value_store.context(CheckPluginName("ntp_time"), None):
        assert list(check_ntp_summary({}, section)) == [
            Result(state=State.OK, summary='Time since last sync: N/A (started monitoring)')
        ]
