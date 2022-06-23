#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

from .agent_based_api.v1 import register, render
from .agent_based_api.v1.type_defs import StringTable
from .utils.aws import AWSLimitsByRegion, parse_aws


def _render_per_second_unit(value: object) -> str:
    return f"{value}/s"


def parse_aws_ebs_limits(string_table: StringTable) -> AWSLimitsByRegion:
    limits_by_region: AWSLimitsByRegion = {}
    for line in parse_aws(string_table):
        resource_key, resource_title, limit, amount, region = line

        if resource_key in [
            "block_store_space_standard",
            "block_store_space_io1",
            "block_store_space_io2",
            "block_store_space_gp2",
            "block_store_space_gp3",
            "block_store_space_sc1",
            "block_store_space_st1",
        ]:
            # Limit has unit TiB, amount is measured in GiB
            limit *= 1024**4
            amount *= 1024**3
            human_readable_func: Callable = render.bytes
        elif resource_key in {"block_store_iops_io1", "block_store_iops_io2"}:
            human_readable_func = _render_per_second_unit
        else:
            human_readable_func = int
        limits_by_region.setdefault(region, []).append(
            [resource_key, resource_title, limit, amount, human_readable_func]
        )
    return limits_by_region


register.agent_section(
    name="aws_ebs_limits",
    parse_function=parse_aws_ebs_limits,
)
