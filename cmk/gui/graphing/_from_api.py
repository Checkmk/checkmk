#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.graphing_engine import ApiPerfometer


class PerfometersFromAPI(Registry[ApiPerfometer]):
    @override
    def plugin_name(self, instance: ApiPerfometer) -> str:
        return instance.name


perfometers_from_api = PerfometersFromAPI()
