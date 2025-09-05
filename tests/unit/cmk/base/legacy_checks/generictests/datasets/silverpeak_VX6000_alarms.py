#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "silverpeak_VX6000"

info = [
    [["4"]],
    [
        ["0", "Tunnel state is Up", "if1"],
        ["2", "System BYPASS mode", "mysystem"],
        ["4", "Tunnel state is Down", "to_sp01-dnd_WAN-WAN"],
        ["8", "Disk is not in service", "mydisk"],
    ],
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "4 active alarms. OK: 1, WARN: 1, CRIT: 1, UNKNOWN: 1", []),
                (0, "\nAlarm: Tunnel state is Up, Alarm-Source: if1, Severity: info", []),
                (1, "\nAlarm: System BYPASS mode, Alarm-Source: mysystem, Severity: minor", []),
                (
                    2,
                    "\nAlarm: Tunnel state is Down, Alarm-Source: to_sp01-dnd_WAN-WAN, Severity: critical",
                    [],
                ),
                (
                    3,
                    "\nAlarm: Disk is not in service, Alarm-Source: mydisk, Severity: indeterminate",
                    [],
                ),
            ],
        )
    ]
}
