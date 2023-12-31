#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


hp_proliant_status2nagios_map = {
    "unknown": 3,
    "other": 3,
    "ok": 0,
    "degraded": 2,
    "failed": 2,
    "disabled": 1,
}


def sanitize_item(item: str) -> str:
    r"""Sanitize null byte in item

    We observed some devices to send "\x00" (null-byte) as their name.
    Not all components delt well with it, so we replace it here
    with r"\x00" (literal backslash-x-zero-zero).
    As of Checkmk 2.3, this should in fact no longer be necessary.
    """
    return item.replace("\x00", r"\x00")
