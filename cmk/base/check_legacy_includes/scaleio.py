#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# tyxpe: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# pylint: disable=no-else-return


def parse_scaleio(info, section):
    parsed: dict = {}
    sys_id = ""
    for line in info:
        if line[0].startswith(section):
            sys_id = line[1].replace(":", "")
            parsed[sys_id] = {}
        elif sys_id in parsed:
            parsed[sys_id][line[0]] = line[1:]
    return parsed


# This converts data into MB for our df.include
def convert_scaleio_space(unit, value):
    if unit == "Bytes":
        return value / 1024.0**2
    elif unit == "KB":
        return value / 1024.0
    elif unit == "MB":
        return value
    elif unit == "GB":
        return value * 1024
    elif unit == "TB":
        return value * 1024 * 1024
    return None


# Values can be in every unit. We need Bytes for
# diskstat.include
def convert_to_bytes(tp, unit):
    if unit == "Bytes":
        return tp
    elif unit == "KB":
        return tp * 1024
    elif unit == "MB":
        return tp * 1024 * 1024
    elif unit == "GB":
        return tp * 1024 * 1024 * 1024
    elif unit == "TB":
        return tp * 1024 * 1024 * 1024 * 1024
    return None


def get_disks(item, read_data, write_data):
    read_tp = convert_to_bytes(int(read_data[-3].strip("(")), read_data[-2].strip(")"))
    write_tp = convert_to_bytes(int(write_data[-3].strip("(")), write_data[-2].strip(")"))

    disks = {
        item: {
            "node": None,
            "read_ios": int(read_data[0]),
            "read_throughput": read_tp,
            "write_ios": int(write_data[0]),
            "write_throughput": write_tp,
        }
    }
    return disks


def get_scaleio_data(item, parsed):
    return parsed.get(item)
