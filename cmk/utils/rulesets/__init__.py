#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container

from cmk.utils.type_defs import ValidatedString


class RuleSetName(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        """
        allow these names

        Unfortunately, we have some WATO rules that contain dots or dashes.
        In order not to break things, we allow those
        """
        return frozenset(
            (
                "drbd.net",
                "drbd.disk",
                "drbd.stats",
                "fileinfo-groups",
                "hpux_snmp_cs.cpu",
                "j4p_performance.mem",
                "j4p_performance.threads",
                "j4p_performance.uptime",
                "j4p_performance.app_state",
                "j4p_performance.app_sess",
                "j4p_performance.serv_req",
            )
        )
