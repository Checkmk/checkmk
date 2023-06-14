#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "cisco_fan"


info = [["Fan_1_rpm", "", "0"], ["Fan_2_rpm", "1", "1"], ["Fan_3_rpm", "999", "2"]]


discovery = {"": [("Fan_2_rpm 1", None)]}


checks = {"": [("Fan_2_rpm 1", {}, [(0, "Status: normal", [])])]}
