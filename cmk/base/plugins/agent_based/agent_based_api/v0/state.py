#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""States of check results
"""
from cmk.base.api.agent_based.checking_types import state, state_worst as worst

OK = state.OK
WARN = state.WARN
CRIT = state.CRIT
UNKNOWN = state.UNKNOWN

del state

__all__ = ["OK", "WARN", "CRIT", "UNKNOWN", "worst"]
