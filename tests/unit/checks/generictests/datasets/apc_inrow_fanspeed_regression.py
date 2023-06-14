#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "apc_inrow_fanspeed"


info = [["518"]]


discovery = {"": [(None, None)]}


checks = {"": [(None, {}, [(0, "Current: 51.80%", [("fanspeed", 51.8, None, None, None, None)])])]}
