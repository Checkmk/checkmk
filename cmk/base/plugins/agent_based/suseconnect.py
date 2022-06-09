#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Agent output examples:# #   .

# Pre-V15 agent output:

# <<<suseconnect:sep(58)>>>
# identifier: SLES
# version: 12.1
# arch: x86_64
# status: Registered
# regcode: banana001
# starts_at: 2015-12-01 00:00:00 UTC
# expires_at: 2019-12-31 00:00:00 UTC
# subscription_status: ACTIVE
# _type: full

# V15+ agent output

# <<<suseconnect:sep(58)>>>
# Installed Products:

#   advanced Systems Management Module
#   (sle-module-adv-systems-management/12/x86_64)

#   Registered

#   sUSE Linux Enterprise Server for SAP Applications 12 SP5
#   (SLES_SAP/12.5/x86_64)

#   Registered

#     Subscription:

#     Regcode: banana005
#     Starts at: 2018-07-01 00:00:00 UTC
#     Expires at: 2021-06-30 00:00:00 UTC
#     Status: ACTIVE
#     Type: full

#   SUSE Package Hub 12
#   (PackageHub/12.5/x86_64)

#   Registered
##.

from .agent_based_api.v1 import register


def _join_line(line):
    return ":".join(line).strip()


def _parse_header(header):

    return dict(zip(["identifier", "version", "architecture"], header[1:-1].split("/")))


def _parse_suseconnect_v15(info):
    map_keys = {
        "Regcode": "registration_code",
        "Starts at": "starts_at",
        "Expires at": "expires_at",
        "Status": "subscription_status",
        "Type": "subscription_type",
    }
    parsed: dict = {}
    specs = {}
    iter_info = iter(info)

    for line in iter_info:
        if line[0].startswith("(") and line[0].endswith(")"):
            parsed_header = _parse_header(line[0])
            specs = parsed.setdefault(parsed_header["identifier"], parsed_header)
            specs["registration_status"] = next(iter_info)[0]
            continue
        if len(line) > 1:
            key, value = line[0], _join_line(line[1:])
            if key in map_keys:
                specs[map_keys[key]] = value

    return parsed


def _parse_suseconnect_pre_v15(info):
    map_keys = {
        "identifier": "identifier",
        "version": "version",
        "arch": "architecture",
        "status": "registration_status",
        "type": "subscription_type",
        "starts_at": "starts_at",
        "expires_at": "expires_at",
        "subscription_status": "subscription_status",
        "regcode": "registration_code",
    }

    parsed = {
        map_keys[line[0]]: _join_line(line[1:])
        for line in info
        if line[0] in map_keys and len(line) > 1
    }

    # Normalise to get data in the format  {identifier: {specs}}
    return {parsed["identifier"]: parsed}


def parse_suseconnect(string_table):

    try:
        first = string_table[0][0]
    except IndexError:
        return {}

    if first == "identifier":
        return _parse_suseconnect_pre_v15(string_table)

    return _parse_suseconnect_v15(string_table)


register.agent_section(
    name="suseconnect",
    parse_function=parse_suseconnect,
)
