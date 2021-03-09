#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# NOTE: This module is for dependency-breaking purposes only, and its contents
# should probably moved somewhere else when there are no import cycles anymore.
# But at the current state of affairs we have no choice, otherwise an
# incremental cleanup is impossible.

from typing import Dict, Text  # pylint: disable=unused-import

from cmk_base.discovered_labels import DiscoveredServiceLabels, DiscoveredHostLabels  # pylint: disable=unused-import
from cmk_base.check_utils import CheckParameters, Item  # pylint: disable=unused-import

# Symbolic representations of states in plugin output
state_markers = ["", "(!)", "(!!)", "(?)"]

# Management board checks
MGMT_ONLY = "mgmt_only"  # Use host address/credentials when it's a SNMP HOST
HOST_PRECEDENCE = "host_precedence"  # Check is only executed for mgmt board (e.g. Managegment Uptime)
HOST_ONLY = "host_only"  # Check is only executed for real SNMP host (e.g. interfaces)

# Is set before check/discovery function execution
_hostname = None  # Host currently being checked
_check_type = None
_service_description = None


class Service(object):
    """Can be used to by the discovery function to tell Checkmk about a new service"""
    def __init__(self, item, parameters=None, service_labels=None, host_labels=None):
        # type: (Item, CheckParameters, DiscoveredServiceLabels, DiscoveredHostLabels) -> None
        self.item = item
        self.parameters = parameters
        self.service_labels = service_labels or DiscoveredServiceLabels()
        self.host_labels = host_labels or DiscoveredHostLabels()


def set_hostname(hostname):
    global _hostname
    _hostname = hostname


def reset_hostname():
    global _hostname
    _hostname = None


def host_name():
    """Returns the name of the host currently being checked or discovered."""
    if _hostname is None:
        raise RuntimeError("host name has not been set")
    return _hostname


def set_service(type_name, descr):
    global _check_type, _service_description
    _check_type = type_name
    _service_description = descr


def check_type():
    """Returns the name of the check type currently being checked."""
    if _check_type is None:
        raise RuntimeError("check type has not been set")
    return _check_type


def service_description():
    """Returns the name of the service currently being checked."""
    if _service_description is None:
        raise RuntimeError("service description has not been set")
    return _service_description
