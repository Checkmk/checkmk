#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.snmp_extended_info import (
    get_device_type_label,
    parse_snmp_extended_info,
)


def test_host_labels():
    section = parse_snmp_extended_info([
        ["_", "fibrechannel switch", "_", "_", "_", "_", "_", "_", "_"],
        ["_", "_", "_", "_", "_", "_", "_", "_", "_"],
    ])
    assert list(get_device_type_label(section)) == [
        HostLabel("cmk/device_type", "fcswitch"),
    ]
