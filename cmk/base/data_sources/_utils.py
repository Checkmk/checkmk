#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Optional

from cmk.utils.type_defs import HostAddress, HostName

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.exceptions import MKIPAddressLookupError

__all__ = ["management_board_ipaddress", "verify_ipaddress"]


def management_board_ipaddress(hostname: HostName) -> Optional[HostAddress]:
    mgmt_ipaddress = config.get_config_cache().get_host_config(hostname).management_address

    if mgmt_ipaddress is None:
        return None

    if not _is_ipaddress(mgmt_ipaddress):
        try:
            return ip_lookup.lookup_ip_address(mgmt_ipaddress)
        except MKIPAddressLookupError:
            return None
    else:
        return mgmt_ipaddress


def verify_ipaddress(address: Optional[HostAddress]) -> None:
    if not address:
        raise MKIPAddressLookupError("Host as no IP address configured.")

    if address in ["0.0.0.0", "::"]:
        raise MKIPAddressLookupError(
            "Failed to lookup IP address and no explicit IP address configured")


def _is_ipaddress(address: Optional[HostAddress]) -> bool:
    if address is None:
        return False

    try:
        socket.inet_pton(socket.AF_INET, address)
        return True
    except socket.error:
        # not a ipv4 address
        pass

    try:
        socket.inet_pton(socket.AF_INET6, address)
        return True
    except socket.error:
        # no ipv6 address either
        return False
