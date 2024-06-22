#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

from cmk.plugins.collection.agent_based.ucs_c_rack_server_faultinst import (
    parse_ucs_c_rack_server_faultinst,
)

checkname = "ucs_c_rack_server_faultinst"

parsed = parse_ucs_c_rack_server_faultinst([])

discovery = {"": [(None, {})]}

checks = {
    "": [
        (None, {}, [(0, "No fault instances found")]),
    ]
}
