#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import startswith

DETECT_APC_NETSHELTERPDU = startswith(
    ".1.3.6.1.2.1.1.2.0",
    ".1.3.6.1.4.1.318.1.1.32",
)


def clean_snmp_name(value: str) -> str:
    r"""Strip null bytes that some APC devices pad their DisplayStrings with.

    Bank, device and outlet names are reported as fixed-width octet strings that
    may be null-terminated (e.g. "B6\x00"). Left unstripped, such a value flows
    into the service item - where an embedded null byte crashes RRD info-file
    creation - or into the check output. See CMK ticket for the APC NetShelter
    APDU series.
    """
    return value.replace("\x00", "").strip()
