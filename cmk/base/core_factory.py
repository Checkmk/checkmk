#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.version import edition, Edition

from cmk.base.core_config import MonitoringCore


def get_licensing_handler_type() -> type[LicensingHandler]:
    if edition() is Edition.CRE:
        from cmk.utils.licensing.registry import get_available_licensing_handler_type
    else:
        from cmk.utils.cee.licensing.registry import (  # type: ignore[import,unused-ignore,no-redef]  # pylint: disable=no-name-in-module,import-error
            get_available_licensing_handler_type,
        )
    return get_available_licensing_handler_type()


def create_core(core_name: str) -> MonitoringCore:
    if core_name == "cmc":
        # pylint: disable=no-name-in-module,import-outside-toplevel
        from cmk.base.cee.microcore_config import CmcPb

        return CmcPb(get_licensing_handler_type())

    if core_name == "nagios":
        from cmk.base.core_nagios import NagiosCore  # pylint: disable=import-outside-toplevel

        return NagiosCore(get_licensing_handler_type())

    raise NotImplementedError
