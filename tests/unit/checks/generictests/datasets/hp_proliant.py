#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "hp_proliant"

info = [["2", "2.60 May 23 2018", "CXX43801XX"]]

discovery = {"": [(None, {})]}

checks = {"": [(None, {}, [(0, "Status: OK, Firmware: 2.60 May 23 2018, S/N: CXX43801XX", [])])]}
