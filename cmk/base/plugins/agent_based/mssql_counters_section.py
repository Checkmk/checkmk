#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
# <<<mssql_counters>>>
# MSSQL_SQLEXPRESS:Buffer_Manager Buffer_cache_hit_ratio 12
# MSSQL_SQLEXPRESS:Databases master Data_File(s)_Size_(KB) 2304
# MSSQL_SQLEXPRESS:Databases master Transactions/sec 13733
# MSSQL_SQLEXPRESS:Databases master Percent_Log_Used 57
# MSSQL_SQLEXPRESS:Databases master Log_File(s)_Size_(KB)
# FOOBAR 170


def parse_mssql_counters(info):
    parsed = {}
    for line in info:
        if len(line) < 4 or line[-1].startswith("ERROR: "):
            continue

        (node_name, obj, counter, instance), values = line[:4], line[4:]

        if obj.endswith(':Databases'):
            obj = obj[:-10]

        if len(values) == 1:
            values = values[0]
            try:
                values = float(values)
            except ValueError:
                try:
                    values = int(values)
                except ValueError:
                    pass

        if counter == "utc_time":
            # mssql returns localized format. great! let's try ...
            try:
                # ... iso 8601
                values = utc_mktime(
                    time.strptime(" ".join(values).split(".")[0], "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                try:
                    # ... german
                    values = utc_mktime(time.strptime(" ".join(values), "%d.%m.%Y %H:%M:%S"))
                except ValueError:
                    pass

        data = parsed.setdefault(node_name, {}).setdefault((obj, instance), {})
        data.setdefault(counter, values)
    return parsed


check_info['mssql_counters'] = {
    'parse_function': parse_mssql_counters,
    'node_info': True,
}
"""
