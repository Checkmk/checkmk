#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def parse_postgres_dbs(info):
    dbs = {}
    inst_name = ""
    lines = iter(info)

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
