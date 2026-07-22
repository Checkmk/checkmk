#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.files import walk_verbatim
from cmk.plugins.diagnostics.lib.topics import TOPIC_BUSINESS_INTELLIGENCE

_BI_CACHE = "tmp/check_mk/bi_cache"


def _collect_bi_runtime_data(context: CollectContext) -> Iterable[DumpItem]:
    yield from walk_verbatim(context.omd_root / _BI_CACHE, PurePosixPath(_BI_CACHE))


diagnostics_plugin_bi_runtime_data = DiagnosticsPlugin(
    name="bi_runtime_data",
    description=Help("Cached data of Business Intelligence aggregations"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_BUSINESS_INTELLIGENCE,
    handler=_collect_bi_runtime_data,
)
