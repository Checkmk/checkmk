#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import MutableMapping, Sequence

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.aws import (
    function_arn_to_item,
    LambdaFunctionConfiguration,
    LambdaRegionLimits,
    LambdaRegionLimitsSection,
    LambdaSummarySection,
    parse_aws,
)


def parse_aws_lambda_summary(string_table: StringTable) -> LambdaSummarySection:
    return {
        function_arn_to_item(lambda_function["FunctionArn"]): LambdaFunctionConfiguration(
            Timeout=float(lambda_function["Timeout"]),
            MemorySize=float(lambda_function["MemorySize"]),
            CodeSize=float(lambda_function["CodeSize"]),
        )
        for lambda_function in parse_aws(string_table)
    }


register.agent_section(
    name="aws_lambda_summary",
    parse_function=parse_aws_lambda_summary,
)


def parse_aws_lambda_region_limits(string_table: StringTable) -> LambdaRegionLimitsSection:
    parsed: Sequence[Sequence[Sequence[str]]] = [json.loads(" ".join(row)) for row in string_table]
    region_limits: MutableMapping[str, LambdaRegionLimits] = {}
    for region in parsed:
        region_name = region[0][4]  # region must contain limits
        region_limits[region_name] = LambdaRegionLimits(
            **{limit[0]: float(limit[3]) for limit in region}
        )
    return region_limits


register.agent_section(
    name="aws_lambda_region_limits",
    parse_function=parse_aws_lambda_region_limits,
)
