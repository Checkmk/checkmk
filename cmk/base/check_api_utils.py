#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This module is for dependency-breaking purposes only, and its contents
# should probably moved somewhere else when there are no import cycles anymore.
# But at the current state of affairs we have no choice, otherwise an
# incremental cleanup is impossible.

from typing import Optional, Union

from cmk.utils.type_defs import CheckPluginName, CheckPluginNameStr, HostName, Item, ServiceName

from cmk.base.check_utils import LegacyCheckParameters
from cmk.base.discovered_labels import DiscoveredServiceLabels

# Management board checks
MGMT_ONLY = "mgmt_only"  # Use host address/credentials when it's a SNMP HOST
HOST_PRECEDENCE = "host_precedence"  # Check is only executed for mgmt board (e.g. Managegment Uptime)
HOST_ONLY = "host_only"  # Check is only executed for real SNMP host (e.g. interfaces)

# Is set before check/discovery function execution
# Host currently being checked
_hostname: Optional[HostName] = None
_check_type: Optional[CheckPluginNameStr] = None
_service_description: Optional[ServiceName] = None


# Obsolete! Do not confuse with the Service object exposed by the new API.
class Service:
    """Can be used to by the discovery function to tell Checkmk about a new service"""
    def __init__(self,
                 item: Item,
                 parameters: LegacyCheckParameters = None,
                 service_labels: Optional[DiscoveredServiceLabels] = None) -> None:
        self.item = item
        self.parameters = parameters
        self.service_labels = service_labels or DiscoveredServiceLabels()


def set_hostname(hostname: Optional[HostName]) -> None:
    """Set the host name for the function host_name that is part of the Check API.
    host_name is used e.g. by the ps-discovery."""
    global _hostname
    _hostname = hostname


def reset_hostname() -> None:
    global _hostname
    _hostname = None


def host_name() -> HostName:
    """Returns the name of the host currently being checked or discovered."""
    if _hostname is None:
        raise RuntimeError("host name has not been set")
    return _hostname


def set_service(
    type_name: Optional[Union[CheckPluginName, str]],
    descr: Optional[ServiceName],
) -> None:
    global _check_type, _service_description
    _check_type = str(type_name)
    _service_description = descr


def check_type() -> CheckPluginNameStr:
    """Returns the name of the check type currently being checked."""
    if _check_type is None:
        raise RuntimeError("check type has not been set")
    return _check_type


def service_description() -> ServiceName:
    """Returns the name of the service currently being checked."""
    if _service_description is None:
        raise RuntimeError("service description has not been set")
    return _service_description
