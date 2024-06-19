#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.agent_based.v1.type_defs import StringTable

Section = Mapping[str, Sequence[Mapping[str, str]]]


def parse_dbs(string_table: StringTable) -> Section:
    dbs: dict[str, list[Mapping[str, str]]] = {}
    inst_name = ""
    lines = iter(string_table)

    for name, *content in lines:
        if name.startswith("[[[") and name.endswith("]]]"):
            inst_name = "%s/" % name[3:-3].upper()
            continue

        if name == "[databases_start]":
            for name_inner, *_rest in lines:
                if name_inner == "[databases_end]":
                    headers = next(lines)[1:]
                    break
                dbs[f"{inst_name}{name_inner}"] = []

            continue

        item = f"{inst_name}{name}"
        if item in dbs:  # Templates are ignored
            dbs[item].append(dict(zip(headers, content)))

    return dbs
