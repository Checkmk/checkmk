#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import ServiceID
from cmk.discover_plugins import PluginLocation


@dataclass(frozen=True, kw_only=True)
class HostCheckConfig:
    delay_precompile: bool
    src: str
    dst: str
    verify_site_python: bool
    locations: list[PluginLocation]
    checks_to_load: list[str]
    # Services excluded from the core configuration by the "Disabled services"
    # ruleset.  The host check cannot determine these itself: it only loads the
    # plug-ins of the services it is supposed to check, and without the plug-in
    # there is no service name to match the ruleset against (CMK-37190).
    disabled_service_ids: list[ServiceID]
    ipaddresses: dict[HostName, HostAddress]
    ipv6addresses: dict[HostName, HostAddress]
    hostname: HostName
