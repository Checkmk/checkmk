#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ..agent_based_api.v1 import (
    all_of,
    any_of,
    contains,
    equals,
    exists,
    not_contains,
    not_equals,
    not_exists,
    not_startswith,
    startswith,
)

# We are not sure how to safely detect the UCD SNMP Daemon. We know that
# it is mainly used on Linux, but not only. But fetching and OID outside
# of the info area for scanning is not a good idea. It will slow down
# scans for *all* hosts.

#   ---ucd cpu load---------------------------------------------------------

# We prefer HOST-RESOURCES-MIB implementation but not in case
# of check 'ucd_cpu_load' because the HR-MIB has not data
# about cpu load

#   ---general ucd/hr-------------------------------------------------------

HR = exists(".1.3.6.1.2.1.25.1.1.0")

_NOT_HR = not_exists(".1.3.6.1.2.1.25.1.1.0")

UCD = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "linux"),
    contains(".1.3.6.1.2.1.1.1.0", "cmc-tc"),
    contains(".1.3.6.1.2.1.1.1.0", "hp onboard administrator"),
    contains(".1.3.6.1.2.1.1.1.0", "barracuda"),
    contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    contains(".1.3.6.1.2.1.1.1.0", "genugate"),
    contains(".1.3.6.1.2.1.1.1.0", "bomgar"),
    contains(".1.3.6.1.2.1.1.1.0", "pulse secure"),
    contains(".1.3.6.1.2.1.1.1.0", "microsens"),
    all_of(  # Artec email archive appliances
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        contains(".1.3.6.1.2.1.1.1.0", "version"),
        contains(".1.3.6.1.2.1.1.1.0", "serial"),
    ),
    all_of(
        equals(".1.3.6.1.2.1.1.1.0", ""),
        exists(".1.3.6.1.4.1.2021.*"),
    ),
)

_NOT_UCD = all_of(
    # This is an explicit negation of the constant above.
    # We don't have a generic negation function as we want
    # discourage constructs like this.
    # In the future this will be acomplished using the 'supersedes'
    # feature (according to CMK-4232), and this can be removed.
    not_contains(".1.3.6.1.2.1.1.1.0", "linux"),
    not_contains(".1.3.6.1.2.1.1.1.0", "cmc-tc"),
    not_contains(".1.3.6.1.2.1.1.1.0", "hp onboard administrator"),
    not_contains(".1.3.6.1.2.1.1.1.0", "barracuda"),
    not_contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    not_contains(".1.3.6.1.2.1.1.1.0", "genugate"),
    not_contains(".1.3.6.1.2.1.1.1.0", "bomgar"),
    not_contains(".1.3.6.1.2.1.1.1.0", "pulse secure"),
    not_contains(".1.3.6.1.2.1.1.1.0", "microsens"),
    any_of(  # Artec email archive appliances
        not_equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        not_contains(".1.3.6.1.2.1.1.1.0", "version"),
        not_contains(".1.3.6.1.2.1.1.1.0", "serial"),
    ),
)

PREFER_HR_ELSE_UCD = all_of(UCD, _NOT_HR)

#   ---helper---------------------------------------------------------------

# Within _is_ucd or _is_ucd_mem we make use of a whitelist
# in order to expand this list of devices easily.

_UCD_MEM = any_of(
    # Devices for which ucd_mem should be used
    # if and only if HR-table is not available
    all_of(
        contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
        not_exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    all_of(
        contains(".1.3.6.1.2.1.1.1.0", "ironport model c3"),
        not_exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    all_of(
        contains(".1.3.6.1.2.1.1.1.0", "bomgar"),
        not_exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    all_of(
        # Astaro and Synology are Linux but should use hr_mem
        # Otherwise Cache/Buffers are included in used memory
        # generating critical state
        not_startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072."),
        # Otherwise use ucd_mem for listed devices in UCD.
        UCD,
    ),
)

_NOT_UCD_MEM = all_of(
    # This is an explicit negation of the constant above.
    # We don't have a generic negation function as we want
    # discourage constructs like this.
    # In the future this will be acomplished using the 'supersedes'
    # feature (according to CMK-4232), and this can be removed.
    any_of(
        not_contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
        exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    any_of(
        not_contains(".1.3.6.1.2.1.1.1.0", "ironport model c3"),
        exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    any_of(
        not_contains(".1.3.6.1.2.1.1.1.0", "bomgar"),
        exists(".1.3.6.1.2.1.25.1.1.0"),
    ),
    any_of(
        # Astaro and Synology are Linux but should use hr_mem
        # Otherwise Cache/Buffers are included in used memory
        # generating critical state
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072."),
        # Otherwise use ucd_mem for listed devices in UCD.
        _NOT_UCD,
    ),
)

# Some devices report incorrect data on both HR and UCD, eg. F5 BigIP
_NOT_BROKEN_MEM = all_of(
    not_startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375"),
    not_startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2620"),
)

#   ---memory---------------------------------------------------------------

USE_UCD_MEM = all_of(_NOT_BROKEN_MEM, _UCD_MEM)

USE_HR_MEM = all_of(_NOT_BROKEN_MEM, _NOT_UCD_MEM)
