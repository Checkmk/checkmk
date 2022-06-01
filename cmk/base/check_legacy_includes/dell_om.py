#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# The OpenManage module attaches itself to the SNMP agent of the
# operating system. We trigger on all Windows and Linux systems.
# This is not optimal but still enough for excluding network
# devices and similar stuff


def scan_dell_om(oid):
    return (
        "Open Manage" in oid(".1.3.6.1.2.1.1.1.0")
        or "Linux" in oid(".1.3.6.1.2.1.1.1.0")
        or "Software: Windows" in oid(".1.3.6.1.2.1.1.1.0")
    )


def parse_omreport(info):
    result = {}
    current_obj: dict = {}

    def insert(obj):
        result[obj["ID"]] = obj.copy()
        obj.clear()

    for line in info:
        try:
            idx = line.index(":")
        except ValueError:
            # no colon in the line
            continue
        key = " ".join(line[:idx])
        value = " ".join(line[idx + 1 :])
        if key == "ID" and current_obj:
            insert(current_obj)

        current_obj[key] = value

    insert(current_obj)
    return result


def status_translate_omreport(code):
    return {"ok": 0, "non-critical": 1, "critical": 2, "not found": 3}.get(code.lower(), 2)
