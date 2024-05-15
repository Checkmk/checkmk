#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1.type_defs import StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_couchbase_lines(string_table: StringTable) -> Section:
    return {data["name"]: data for line in string_table if line and (data := json.loads(line[0]))}
