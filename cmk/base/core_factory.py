#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.core_config import MonitoringCore


def create_core(core_name: str) -> MonitoringCore:
    if core_name == "cmc":
        # pylint: disable=no-name-in-module,import-outside-toplevel
        from cmk.base.cee.microcore_config import CmcPb

        return CmcPb()

    if core_name == "nagios":
        from cmk.base.core_nagios import NagiosCore  # pylint: disable=import-outside-toplevel

        return NagiosCore()

    raise NotImplementedError
