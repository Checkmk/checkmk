#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.utils.log import console

ConfigurationWarnings = list[str]

g_configuration_warnings: ConfigurationWarnings = []


def initialize() -> None:
    global g_configuration_warnings
    g_configuration_warnings = []


def warn(text: str) -> None:
    g_configuration_warnings.append(text)
    console.warning("\n%s", text, stream=sys.stdout)


def get_configuration() -> ConfigurationWarnings:
    adjusted_warnings = list(set(g_configuration_warnings))

    if (num_warnings := len(adjusted_warnings)) > 10:
        warnings = adjusted_warnings[:10] + [
            "%d further warnings have been omitted" % (num_warnings - 10)
        ]
    else:
        warnings = adjusted_warnings

    return warnings
