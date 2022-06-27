#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Format of a response string according to the manufacturer documentation:
# status@item_count@item[1].name@item[1].value@...item[n].name@item[n].value@$
# Beware, though: Item names are not always unique!


def parse_ddn_s2a_api_response(info):
    response_string = " ".join(info[0])
    raw_fields = response_string.split("@")

    parsed: dict = {}
    for field_name, field_value in zip(raw_fields[2:-2:2], raw_fields[3:-1:2]):
        parsed.setdefault(field_name, []).append(field_value)
    return parsed
