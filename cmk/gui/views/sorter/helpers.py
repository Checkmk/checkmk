#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.num_split import cmp_num_split as _cmp_num_split
from cmk.gui.type_defs import ColumnName, Row, SorterFunction


def cmp_simple_number(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = r1[column]
    v2 = r2[column]
    return (v1 > v2) - (v1 < v2)


def cmp_num_split(column: ColumnName, r1: Row, r2: Row) -> int:
    return _cmp_num_split(r1[column].lower(), r2[column].lower())


def cmp_simple_string(column: ColumnName, r1: Row, r2: Row) -> int:
    v1, v2 = r1.get(column, ""), r2.get(column, "")
    return cmp_insensitive_string(v1, v2)


def cmp_insensitive_string(v1: str, v2: str) -> int:
    c = (v1.lower() > v2.lower()) - (v1.lower() < v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return (v1 > v2) - (v1 < v2)
    return c


def cmp_string_list(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = "".join(r1.get(column, []))
    v2 = "".join(r2.get(column, []))
    return cmp_insensitive_string(v1, v2)


def cmp_custom_variable(r1: Row, r2: Row, key: str, cmp_func: SorterFunction) -> int:
    return (_get_custom_var(r1, key) > _get_custom_var(r2, key)) - (
        _get_custom_var(r1, key) < _get_custom_var(r2, key)
    )


def cmp_ip_address(column: ColumnName, r1: Row, r2: Row) -> int:
    return compare_ips(r1.get(column, ""), r2.get(column, ""))


def compare_ips(ip1: str, ip2: str) -> int:
    def split_ip(ip: str) -> tuple:
        try:
            return tuple(int(part) for part in ip.split("."))
        except ValueError:
            # Make hostnames comparable with IPv4 address representations
            return (255, 255, 255, 255, ip)

    v1, v2 = split_ip(ip1), split_ip(ip2)
    return (v1 > v2) - (v1 < v2)


def _get_custom_var(row: Row, key: str) -> str:
    return row["custom_variables"].get(key, "")
