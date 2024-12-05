#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric translations for different checks"""

from cmk.graphing.v1 import translations

translation_redfish_outlets = translations.Translation(
    name="redfish_outlets",
    check_commands=[
        translations.PassiveCheck("redfish_outlets"),
    ],
    translations={
        "energy": translations.ScaleBy(
            1000,
        ),
    },
)
