#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def parse_redis_info(info):
    parsed: dict = {}
    instance = {}
    inst_section = {}
    for line in info:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            name, host, port = line[0][3:-3].split("|")
            instance = parsed.setdefault(
                name.replace(";", ":"),
                {
                    "host": host,
                    "port": port,
                },
            )
            continue

        if not instance:
            continue

        if line[0].startswith("#"):
            inst_section = instance.setdefault(line[0].split()[-1], {})
            continue

        raw_value = ":".join(line[1:])
        try:
            value: int | float = int(raw_value)
        except ValueError:
            pass
        else:
            inst_section[line[0]] = value
            continue

        try:
            value = float(raw_value)
        except ValueError:
            pass
        else:
            inst_section[line[0]] = value
            continue

        inst_section[line[0]] = raw_value

    return parsed
