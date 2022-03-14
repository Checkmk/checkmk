#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.df import FSBlocks


def str_to_mebibyte(value: int) -> float:
    return value / (1024.0**2)


def parse_ceph_df_json(string_table: StringTable) -> FSBlocks:
    # string_table[0][0] contains the version string for possible future compatibilitly checks
    ceph_df = json.loads(string_table[1][0])
    summary = list(ceph_df["stats_by_class"].values())[0]
    mps = []
    mps.append(
        (
            "SUMMARY",
            str_to_mebibyte(summary["total_bytes"]),
            str_to_mebibyte(summary["total_avail_bytes"]),
            0,
        )
    )
    mps.extend(
        [
            (
                pool["name"],
                str_to_mebibyte(pool["stats"]["max_avail"])
                + str_to_mebibyte(pool["stats"]["bytes_used"]),
                str_to_mebibyte(pool["stats"]["max_avail"]),
                0,
            )
            for pool in ceph_df["pools"]
        ]
    )
    return mps


register.agent_section(
    name="ceph_df_json",
    parse_function=parse_ceph_df_json,
    parsed_section_name="ceph_df",
    supersedes=["ceph_df"],
)
