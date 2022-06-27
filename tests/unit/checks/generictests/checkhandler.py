#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class CheckHandler:
    """Collect the info on all checks"""

    def __init__(self) -> None:
        self.cache: dict = {}

    def get_applicables(self, checkname, check_info):
        """get a list of names of all (sub)checks that apply"""
        if checkname in self.cache:
            return self.cache[checkname]
        found = [s for s in check_info.keys() if s.split(".")[0] == checkname]
        return self.cache.setdefault(checkname, found)


checkhandler = CheckHandler()
