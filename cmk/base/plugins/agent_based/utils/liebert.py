#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

from ..agent_based_api.v0 import (
    startswith,)
from ..agent_based_api.v0.type_defs import (
    SNMPStringTable,)

ParsedSection = Dict[str, str]

DETECT_LIEBERT = startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.476.1.42')


def parse_liebert_without_unit(string_table: SNMPStringTable, type_func=float) -> ParsedSection:

    parsed = {}
    used_names = set()

    def get_item_name(name):
        counter = 2
        new_name = name
        while True:
            if new_name in used_names:
                new_name = "%s %d" % (name, counter)
                counter += 1
            else:
                used_names.add(new_name)
                break
        return new_name

    for line in string_table[0]:
        for element in zip(line[0::2], line[1::2]):
            if not element[0]:
                continue
            name = get_item_name(element[0])
            try:
                parsed[name] = type_func(element[1])
            except ValueError:
                continue

    return parsed
