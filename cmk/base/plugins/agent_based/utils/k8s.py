#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

####################################################################################
# NOTE: This file will be removed in Checkmk version 2.3. CMK-11309
####################################################################################


import json
from typing import Dict

from ..agent_based_api.v1.type_defs import StringTable


def parse_json(string_table: StringTable) -> Dict:
    data = json.loads(string_table[0][0])
    assert isinstance(data, dict)
    return data
