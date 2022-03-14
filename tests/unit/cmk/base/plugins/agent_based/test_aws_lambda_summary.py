#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.aws_lambda_summary import parse_aws_lambda_summary
from cmk.base.plugins.agent_based.utils.aws import LambdaFunctionConfiguration, LambdaSummarySection

_STRING_TABLE_AWS_LAMBDA_SUMMARY = [
    [
        '[{"FunctionName":',
        '"my_python_test_function",',
        '"FunctionArn":',
        '"arn:aws:lambda:eu-central-1:710145618630:function:my_python_test_function",',
        '"Runtime":',
        '"python3.8",',
        '"Role":',
        '"arn:aws:iam::710145618630:role/service-role/my_python_test_function-role-uehtayw3",',
        '"Handler":',
        '"lambda_function.lambda_handler",',
        '"CodeSize":',
        "375,",
        '"Description":',
        '"",',
        '"Timeout":',
        "1,",
        '"MemorySize":',
        "128,",
        '"LastModified":',
        '"2021-06-28T09:13:25.232+0000",',
        '"CodeSha256":',
        '"1EwrRdaekBcaqZ+4V9ymuvyciq+xQOCu8gzLmB2ubS0=",',
        '"Version":',
        '"$LATEST",',
        '"TracingConfig":',
        '{"Mode":',
        '"PassThrough"},',
        '"RevisionId":',
        '"7f26e9a4-b0e2-4ff4-a6a1-7c52a90bd689"}]',
    ],
    [
        '[{"FunctionName":',
        '"myLambdaTestFunction",',
        '"FunctionArn":',
        '"arn:aws:lambda:eu-north-1:710145618630:function:myLambdaTestFunction",',
        '"Runtime":',
        '"python3.8",',
        '"Role":',
        '"arn:aws:iam::710145618630:role/service-role/myLambdaTestFunction-role-jp7mgseb",',
        '"Handler":',
        '"lambda_function.lambda_handler",',
        '"CodeSize":',
        "299,",
        '"Description":',
        '"",',
        '"Timeout":',
        "1,",
        '"MemorySize":',
        "128,",
        '"LastModified":',
        '"2021-06-24T12:46:32.415+0000",',
        '"CodeSha256":',
        '"fI06ZlRH/KN6Ra3twvdRllUYaxv182Tjx0qNWNlKIhI=",',
        '"Version":',
        '"$LATEST",',
        '"TracingConfig":',
        '{"Mode":',
        '"PassThrough"},',
        '"RevisionId":',
        '"2b10d3f5-827c-4e21-9647-c61ba360c8eb"}]',
    ],
]


@pytest.mark.parametrize(
    "string_table_aws_lambda_summary, results",
    [
        (
            _STRING_TABLE_AWS_LAMBDA_SUMMARY,
            {
                "eu-central-1 my_python_test_function": LambdaFunctionConfiguration(
                    Timeout=1.0, MemorySize=128.0, CodeSize=375.0
                ),
                "eu-north-1 myLambdaTestFunction": LambdaFunctionConfiguration(
                    Timeout=1.0, MemorySize=128.0, CodeSize=299.0
                ),
            },
        ),
    ],
)
def test_parse_aws_lambda_summary(
    string_table_aws_lambda_summary: StringTable, results: LambdaSummarySection
) -> None:
    assert parse_aws_lambda_summary(string_table_aws_lambda_summary) == results
