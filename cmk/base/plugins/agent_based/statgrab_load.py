# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# # This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# # conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu import Load, Section


def parse_statgrab_load(string_table: StringTable) -> Section:
    return Section(
        load=Load(
            **{
                time_frame.replace(
                    "min",
                    "load",
                    1,
                ): float(load)
                for time_frame, load in string_table
            }
        ),
        num_cpus=1,
    )


register.agent_section(
    name="statgrab_load",
    parsed_section_name="cpu",
    parse_function=parse_statgrab_load,
)
