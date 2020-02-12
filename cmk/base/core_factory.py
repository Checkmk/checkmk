#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Dict  # pylint: disable=unused-import

import cmk.base.config
import cmk.base.core_config as core_config  # pylint: disable=unused-import


def create_core(options=None):
    # type: (Optional[Dict]) -> core_config.MonitoringCore
    if cmk.base.config.monitoring_core == "cmc":
        from cmk.base.cee.core_cmc import CMC  # pylint: disable=no-name-in-module
        return CMC(options)
    from cmk.base.core_nagios import NagiosCore
    return NagiosCore()
