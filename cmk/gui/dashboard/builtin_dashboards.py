#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .type_defs import DashboardConfig, DashboardName

# Declare constants to be used in the definitions of the dashboards
GROW = 0
MAX = -1

builtin_dashboards: dict[DashboardName, DashboardConfig] = {}
