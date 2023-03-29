#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "alcatel_cpu"

info = [["17", "doesnt matter", "doesnt matter"], ["doesnt matter"]]

discovery = {"": [(None, (90.0, 95.0))]}

checks = {"": [(None, (90.0, 95.0), [(0, "total: 17.0%", [("util", 17, 90.0, 95.0, 0, 100)])])]}
