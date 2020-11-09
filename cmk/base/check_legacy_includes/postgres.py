#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-break


def parse_postgres_dbs(info):
    dbs = {}
    inst_name = ""
    lines = iter(info)
    try:
        while True:
            line = next(lines)
            if line[0].startswith("[[[") and line[0].endswith("]]]"):
                inst_name = "%s/" % line[0][3:-3].upper()

            elif line[0] == "[databases_start]":
                while True:
                    line = next(lines)
                    if line[0] == "[databases_end]":
                        headers = next(lines)[1:]
                        break
                    else:
                        dbs["%s%s" % (inst_name, line[0])] = []
                continue

            else:
                if "%s%s" % (inst_name, line[0]) in dbs:  # Templates are ignored
                    dbs["%s%s" % (inst_name, line[0])].append(dict(zip(headers, line[1:])))

    except StopIteration:
        pass

    return dbs
