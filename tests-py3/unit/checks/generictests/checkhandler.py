#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

from testlib.debug_utils import cmk_debug_enabled

import cmk.base.config as config
import cmk.base.check_api as check_api


class CheckHandler:
    """Collect the info on all checks"""
    def __init__(self):
        with cmk_debug_enabled():  # fail if any check plugin cannot be loaded!
            config.load_all_checks(check_api.get_check_api_context)

        self.info = copy.deepcopy(config.check_info)
        self.cache = {}

    def get_applicables(self, checkname):
        """get a list of names of all (sub)checks that apply"""
        if checkname in self.cache:
            return self.cache[checkname]
        found = [s for s in self.info.keys() if s.split('.')[0] == checkname]
        return self.cache.setdefault(checkname, found)


checkhandler = CheckHandler()
