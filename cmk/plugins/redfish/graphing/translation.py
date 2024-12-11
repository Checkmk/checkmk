#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
'''Metric translations for different checks'''
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

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
