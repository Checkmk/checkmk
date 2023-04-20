#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The content of this include file has been migrated to cmk/base/plugins/agent_based/utils/ucd_hr_detection.py
# We must keep the functions here for the moment, to keep the auto migration working.


def is_ucd(oid: object) -> bool:
    raise NotImplementedError("already migrated")


#   ---general ucd/hr-------------------------------------------------------


def is_hr(oid: object) -> bool:
    raise NotImplementedError("already migrated")


def prefer_hr_else_ucd(oid):
    raise NotImplementedError("already migrated")


#   ---memory---------------------------------------------------------------


def is_ucd_mem(oid: object) -> bool:
    raise NotImplementedError("already migrated")
