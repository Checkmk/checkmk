#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_oracle_instance = translations.Translation(
    name="oracle_instance",
    check_commands=[
        translations.PassiveCheck("oracle_instance"),
    ],
    translations={
        "fs_size": translations.RenameTo(
            "oracle_pdb_total_size",
        ),
    },
)
