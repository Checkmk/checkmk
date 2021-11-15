#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.ucs_c_rack_server_faultinst import (
    parse_ucs_c_rack_server_faultinst,
)

checkname = 'ucs_c_rack_server_faultinst'

parsed = parse_ucs_c_rack_server_faultinst([])

discovery = {'': [(None, {})]}

checks = {'': [(None,
                {},
                [(0, "No fault instances found")]),
               ]}
