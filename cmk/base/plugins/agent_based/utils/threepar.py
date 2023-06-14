#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping
from typing import Any

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


def parse_3par(
    string_table: StringTable,
) -> Mapping[str, Any]:
    try:
        return json.loads(string_table[0][0])
    except IndexError:
        return {}
