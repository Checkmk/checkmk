#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.base.core_config import MonitoringCore
from cmk.ccc.version import Edition, edition
from cmk.utils import paths
from cmk.utils.licensing.handler import LicensingHandler


def get_licensing_handler_type() -> type[LicensingHandler]:
    if edition(paths.omd_root) is Edition.CRE:
        from cmk.utils.licensing.registry import get_available_licensing_handler_type
    else:
        from cmk.utils.cee.licensing.registry import (  # type: ignore[import,unused-ignore,no-redef]
            get_available_licensing_handler_type,
        )
    return get_available_licensing_handler_type()


def create_core(core_name: str) -> MonitoringCore:
    if core_name == "cmc":
        from cmk.base.cee.microcore_config import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
            CmcPb,
        )

        return CmcPb(get_licensing_handler_type())

    if core_name == "nagios":
        from cmk.base.core_nagios import NagiosCore

        return NagiosCore(get_licensing_handler_type())

    raise NotImplementedError
