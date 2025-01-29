#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "tplink_poe_summary"

info = [["150"]]

discovery = {"": [(None, {})]}

checks = {"": [(None, {}, [(0, "15.00 W", [("power", 15.0)])])]}
