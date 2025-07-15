#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.discover_plugins import PluginLocation


@dataclass(frozen=True, kw_only=True)
class HostCheckConfig:
    delay_precompile: bool
    src: str
    dst: str
    verify_site_python: bool
    locations: list[PluginLocation]
    checks_to_load: list[str]
    ipaddresses: dict[HostName, HostAddress]
    ipv6addresses: dict[HostName, HostAddress]
    hostname: HostName
