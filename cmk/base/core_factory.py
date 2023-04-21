#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.version import is_raw_edition

from cmk.base.core_config import MonitoringCore


def create_core(core_name: str) -> MonitoringCore:
    if core_name == "cmc":
        # pylint: disable=no-name-in-module,import-outside-toplevel
        from cmk.utils.cee.licensing.registry import get_available_licensing_handler_type

        from cmk.base.cee.microcore_config import CmcPb

        return CmcPb(get_available_licensing_handler_type())

    if core_name == "nagios":
        from cmk.base.core_nagios import NagiosCore  # pylint: disable=import-outside-toplevel

        if is_raw_edition():
            from cmk.utils.licensing.registry import get_available_licensing_handler_type
        else:
            from cmk.utils.cee.licensing.registry import get_available_licensing_handler_type

        return NagiosCore(get_available_licensing_handler_type())

    raise NotImplementedError
