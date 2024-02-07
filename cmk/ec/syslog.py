#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping


class SyslogPriority:
    NAMES: Mapping[int, str] = {
        0: "emerg",
        1: "alert",
        2: "crit",
        3: "err",
        4: "warning",
        5: "notice",
        6: "info",
        7: "debug",
    }

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"SyslogPriority({self.value})"

    def __str__(self) -> str:
        try:
            return self.NAMES[self.value]
        except KeyError:
            return f"(unknown priority {self.value})"


class SyslogFacility:
    NAMES: Mapping[int, str] = {
        0: "kern",
        1: "user",
        2: "mail",
        3: "daemon",
        4: "auth",
        5: "syslog",
        6: "lpr",
        7: "news",
        8: "uucp",
        9: "cron",
        10: "authpriv",
        11: "ftp",
        12: "ntp",
        13: "logaudit",
        14: "logalert",
        15: "clock",
        16: "local0",
        17: "local1",
        18: "local2",
        19: "local3",
        20: "local4",
        21: "local5",
        22: "local6",
        23: "local7",
        30: "logfile",  # HACK because the RFC says that facilities MUST be in the range 0-23
        31: "snmptrap",  # everything above that is for internal use. see: https://datatracker.ietf.org/doc/html/rfc5424#section-6.2.1
    }

    def __init__(self, value: int) -> None:
        if value not in self.NAMES:
            raise ValueError(
                f"Value must be one of the following {', '.join(str(key) for key in self.NAMES)}"
            )
        self.value = int(value)

    def __repr__(self) -> str:
        return f"SyslogFacility({self.value})"

    def __str__(self) -> str:
        try:
            return self.NAMES[self.value]
        except KeyError:
            return f"(unknown facility {self.value})"
