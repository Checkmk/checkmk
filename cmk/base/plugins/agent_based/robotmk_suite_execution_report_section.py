#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.robotmk_suite_execution_report import SuiteExecutionReport


def parse(string_table: StringTable) -> Sequence[SuiteExecutionReport]:
    return [SuiteExecutionReport.model_validate_json(line[0]) for line in string_table]


register.agent_section(
    name="robotmk_suite_execution_report",
    parse_function=parse,
)
