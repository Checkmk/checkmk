#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Callable, Sequence
from typing import Final

from cmk.ccc import tty
from cmk.utils.log import console

type IssueConfigWarning = Callable[[str], None]


ConfigurationWarnings = list[str]

g_configuration_warnings: ConfigurationWarnings = []


def initialize() -> None:
    global g_configuration_warnings
    g_configuration_warnings = []


def warn(text: str) -> None:
    g_configuration_warnings.append(text)
    console.warning(
        tty.format_warning(f"\n{text}"),
        file=sys.stderr,
    )


def get_configuration(
    *,  # kw only for now b/c the naming is quite creative here.
    additional_warnings: Sequence[str],
) -> ConfigurationWarnings:
    adjusted_warnings = list({*g_configuration_warnings, *additional_warnings})
    max_warnings: Final = 10
    num_warnings = len(adjusted_warnings)
    return (
        adjusted_warnings[:max_warnings]
        + [f"{num_warnings - max_warnings} further warnings have been omitted"]
        if num_warnings > max_warnings
        else adjusted_warnings
    )
