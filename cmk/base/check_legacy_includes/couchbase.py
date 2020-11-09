#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
import json


def parse_couchbase_lines(info):
    parsed = {}
    for line in info:
        try:
            data = json.loads(line[0])
        except (IndexError, ValueError):
            continue
        parsed[data["name"]] = data
    return parsed
