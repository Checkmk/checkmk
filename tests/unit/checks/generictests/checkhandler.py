#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition


class CheckHandler:
    """Collect the info on all checks"""

    def __init__(self) -> None:
        self.cache: dict[str, list[str]] = {}

    def get_applicables(
        self, checkname: str, check_info: dict[str, LegacyCheckDefinition]
    ) -> list[str]:
        """get a list of names of all (sub)checks that apply"""
        if checkname in self.cache:
            return self.cache[checkname]
        found = [s for s in check_info.keys() if s.split(".")[0] == checkname]
        return self.cache.setdefault(checkname, found)


checkhandler = CheckHandler()
