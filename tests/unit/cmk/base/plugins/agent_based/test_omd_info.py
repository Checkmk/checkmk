#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict

from cmk.base.plugins.agent_based import omd_info


def test_label_with_sites():
    section = {"sites": {"a": {"foo": "bar"}}}
    assert list(omd_info.host_label_omd_info(section)) == [
        omd_info.HostLabel("cmk/check_mk_server", "yes")
    ]


def test_no_label_without_sites():
    assert not list(omd_info.host_label_omd_info({"sites": {}}))
