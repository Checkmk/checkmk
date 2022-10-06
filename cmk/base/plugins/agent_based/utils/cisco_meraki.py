#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence

from ..agent_based_api.v1.type_defs import StringTable

MerakiAPIData = Mapping[str, object]


def load_json(string_table: StringTable) -> Sequence[MerakiAPIData]:
    try:
        return json.loads(string_table[0][0])
    except (IndexError, json.decoder.JSONDecodeError):
        return []
