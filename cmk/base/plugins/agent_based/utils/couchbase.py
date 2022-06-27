#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Mapping

from ..agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_couchbase_lines(string_table: StringTable) -> Section:
    return {data["name"]: data for line in string_table if line and (data := json.loads(line[0]))}
