#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import Enum

from cmk.rulesets.v1.form_specs import ServiceState


class HAProxyFrontendStatus(Enum):
    OPEN = "OPEN"
    STOP = "STOP"


class HAProxyServerStatus(Enum):
    """
    https://www.haproxy.com/documentation/haproxy-configuration-manual/2-5r1/management/

    Notes:
        * MAINT (resolution) and MAINT (via) are listed explicitly as states in the linked
        documentation, therefore including them in the enum instead of treating them as a partial
        status.
    """

    UP = "UP"
    DOWN = "DOWN"
    NOLB = "NOLB"
    MAINT = "MAINT"
    MAINT_RES = "MAINT (resolution)"
    MAINT_VIA = "MAINT (via)"
    DRAIN = "DRAIN"
    NO_CHECK = "no check"


DEFAULT_FRONTEND_STATES = {
    HAProxyFrontendStatus.OPEN: ServiceState.OK,
    HAProxyFrontendStatus.STOP: ServiceState.CRIT,
}
DEFAULT_SERVER_STATES = {
    HAProxyServerStatus.UP: ServiceState.OK,
    HAProxyServerStatus.DOWN: ServiceState.CRIT,
    HAProxyServerStatus.NOLB: ServiceState.CRIT,
    HAProxyServerStatus.MAINT: ServiceState.CRIT,
    HAProxyServerStatus.MAINT_VIA: ServiceState.WARN,
    HAProxyServerStatus.MAINT_RES: ServiceState.WARN,
    HAProxyServerStatus.DRAIN: ServiceState.CRIT,
    HAProxyServerStatus.NO_CHECK: ServiceState.CRIT,
}
