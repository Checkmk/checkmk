#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.type_defs import CheckPluginNameStr
from cmk.snmplib.type_defs import OID, SNMPDecodedString


def oid_kea(_arg: OID,
            _decoded: Optional[SNMPDecodedString] = None,
            _name: Optional[CheckPluginNameStr] = None) -> Optional[SNMPDecodedString]:
    """OID function of a Kea"""
    return "Kea"


def scan_kea(oid):
    """Scan function scanning for Keas"""
    return oid(".O.I.D") == "Kea"
