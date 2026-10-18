#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This is an unsorted collection of small unrelated helper functions which are
usable in all components of Check_MK

Please try to find a better place for the things you want to put here."""


def pnp_cleanup(s: str) -> str:
    """Quote a string (host name or service name) in PNP4Nagios format

    Because it is used as path element, this needs to be handled as "str" in Python 2 and 3
    """
    return (
        s.replace(" ", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("\x00", "_")
    )
