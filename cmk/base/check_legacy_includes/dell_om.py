#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.agent_based.v2 import StringTable

# The OpenManage module attaches itself to the SNMP agent of the
# operating system. We trigger on all Windows and Linux systems.
# This is not optimal but still enough for excluding network
# devices and similar stuff


def _parse_single_objects(string_table: StringTable) -> Iterable[Mapping[str, str]]:
    current_obj: dict = {}

    for line in string_table:
        try:
            idx = line.index(":")
        except ValueError:
            # no colon in the line
            continue
        key = " ".join(line[:idx])
        value = " ".join(line[idx + 1 :])
        if key == "ID" and current_obj:
            yield current_obj
            current_obj = {}

        current_obj[key] = value

    yield current_obj


def parse_omreport(string_table: StringTable) -> Mapping[str, Mapping[str, str]]:
    return {o["ID"]: o for o in _parse_single_objects(string_table)}


def status_translate_omreport(code: str) -> int:
    return {"ok": 0, "non-critical": 1, "critical": 2, "not found": 3}.get(code.lower(), 2)
