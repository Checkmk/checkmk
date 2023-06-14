#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "netstat"


info = [
    ["tcp", "0", "0", "127.0.0.1.5999", "*.*", "LISTENING"],
    ["tcp", "0", "0", "127.0.0.1.25", "*.*", "LISTENING"],
    ["tcp", "0", "0", "127.0.0.1.587", "*.*", "LISTENING"],
    ["udp", "*.*", "0.0.0.0:*"],
    ["udp", "*.68", "0.0.0.0:*"],
    ["udp", "*.631", "0.0.0.0:*"],
]


discovery = {"": []}

checks = {"": [("connections", {}, [(0, "Matching entries found: 6", [("connections", 6)])])]}
