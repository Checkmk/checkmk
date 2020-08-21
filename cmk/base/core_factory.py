#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Dict

import cmk.base.config
from cmk.base.core_config import MonitoringCore


def create_core(options: Optional[Dict] = None) -> MonitoringCore:
    if cmk.base.config.monitoring_core == "cmc":
        from cmk.base.cee.core_cmc import CMC  # pylint: disable=no-name-in-module,import-outside-toplevel
        return CMC(options)
    from cmk.base.core_nagios import NagiosCore  # pylint: disable=import-outside-toplevel
    return NagiosCore()
