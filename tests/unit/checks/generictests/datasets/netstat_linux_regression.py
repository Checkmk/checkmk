#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "netstat"


info = [
    ["tcp", "0", "0", "0.0.0.0:111", "0.0.0.0:*", "LISTENING"],
    ["tcp", "0", "0", "172.17.40.64:58821", "172.17.1.190:8360", "ESTABLISHED"],
    ["tcp", "0", "0", "172.17.40.64:6556", "172.17.40.64:36577", "TIME_WAIT"],
    ["udp", "0", "0", "fe80::250:56ff:fea2:123", ":::*"],
]


discovery = {"": []}

checks = {"": [("connections", {}, [(0, "Matching entries found: 4", [("connections", 4)])])]}
