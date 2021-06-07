#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.aws import (
    function_arn_to_item,
    parse_aws,
    LambdaSummarySection,
)
from .agent_based_api.v1.type_defs import StringTable


def parse_aws_lambda_summary(string_table: StringTable) -> LambdaSummarySection:
    parsed = parse_aws(string_table)
    return {
        function_arn_to_item(lambda_function["FunctionArn"]): float(lambda_function["Timeout"])
        for lambda_function in parsed
    }


register.agent_section(
    name="aws_lambda_summary",
    parse_function=parse_aws_lambda_summary,
)
