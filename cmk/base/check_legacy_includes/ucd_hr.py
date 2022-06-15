#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The content of this include file has been migrated to cmk/base/plugins/agent_based/utils/ucd_hr_detection.py
# We must keep the functions here for the moment, to keep the auto migration working.


def is_ucd(oid) -> bool:
    raise NotImplementedError("already migrated")


#   ---general ucd/hr-------------------------------------------------------


def is_hr(oid) -> bool:
    raise NotImplementedError("already migrated")


def prefer_hr_else_ucd(oid):
    raise NotImplementedError("already migrated")


#   ---memory---------------------------------------------------------------


def is_ucd_mem(oid) -> bool:
    raise NotImplementedError("already migrated")


def is_hr_mem(oid) -> bool:
    raise NotImplementedError("already migrated")


#   ---helper---------------------------------------------------------------

# Within _is_ucd or _is_ucd_mem we make use of a whitelist
# in order to expand this list of devices easily.


def _is_ucd(oid) -> bool:
    raise NotImplementedError("already migrated")


def _is_ucd_mem(oid) -> bool:
    raise NotImplementedError("already migrated")


def _ignore_both(oid):
    raise NotImplementedError("already migrated")
