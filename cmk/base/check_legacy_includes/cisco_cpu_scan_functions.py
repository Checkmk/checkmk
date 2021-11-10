#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
#   ---non Nexus devices----------------------------------------------------
#   ---specific Cisco devices-----------------------------------------------


def snmp_scan_cisco_cpu(oid):
    return (
        _is_cisco(oid)
        and (not _is_cisco_nexus(oid) or not bool(oid(".1.3.6.1.4.1.9.9.305.1.1.1.0")))
        and not _has_table_2(oid)
        and (
            bool(oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"))
            or bool(oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1"))
        )
    )


#   ---fallback-------------------------------------------------------------


# the follwoing function was duplicated to cmk/base/plugins/agent_based/cisco_cpu_multiitem.py
def snmp_scan_cisco_cpu_multiitem(oid):
    return _is_cisco(oid) and not _is_cisco_nexus(oid) and _has_table_2(oid)


#   ---Nexus devices--------------------------------------------------------


def snmp_scan_cisco_nexus_cpu(oid):
    return _is_cisco(oid) and _is_cisco_nexus(oid) and bool(oid(".1.3.6.1.4.1.9.9.305.1.1.1.0"))


#   ---old Cisco devices----------------------------------------------------


def snmp_scan_cisco_oldcpu(oid):
    return (
        oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.9.1.1745")
        and _has_table_2(oid)
        and bool(oid(".1.3.6.1.4.1.9.2.1.57.0"))
    )


#   ---helper---------------------------------------------------------------


def _is_cisco(oid):
    return "cisco" in oid(".1.3.6.1.2.1.1.1.0").lower()


def _is_cisco_nexus(oid):
    return "nx-os" in oid(".1.3.6.1.2.1.1.1.0").lower()


def _has_table_2(oid):
    return bool(oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"))
