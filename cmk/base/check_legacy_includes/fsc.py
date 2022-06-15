#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def _is_fsc_or_windows(oid) -> bool:
    # sysObjId is from FSC or Windows or Net-SNMP
    return (
        oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.231")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.311")
        or oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.8072")
    )


def is_fsc(oid) -> bool:
    return _is_fsc_or_windows(oid) and bool(oid(".1.3.6.1.4.1.231.2.10.2.1.1.0"))


def is_fsc_sc2(oid) -> bool:
    return _is_fsc_or_windows(oid) and bool(oid(".1.3.6.1.4.1.231.2.10.2.2.10.1.1.0"))


def is_fsc_fans_prefer_sc2(oid) -> bool:
    return is_fsc(oid) and not bool(oid(".1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.*"))


def is_fsc_temp_prefer_sc2(oid) -> bool:
    return is_fsc(oid) and not bool(oid(".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.*"))
