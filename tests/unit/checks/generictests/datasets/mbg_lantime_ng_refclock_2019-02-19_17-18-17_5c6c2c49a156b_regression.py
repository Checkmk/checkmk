#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "mbg_lantime_ng_refclock"


info = [["1", "15", "3", "2", "101", "0", "0", "0", "0", "0", "not announced"]]


discovery = {"": [("1", None)], "gps": []}


checks = {
    "": [("1", {}, [(1, "Type: tcr511, Usage: primary, State: not synchronized (TCT sync)", [])])]
}
