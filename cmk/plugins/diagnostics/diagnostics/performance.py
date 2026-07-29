#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable
from pathlib import PurePosixPath

import cmk.livestatus_client as livestatus
from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_PERFORMANCE

_CMC_SETTING_KEYS = {
    "cmc_check_helpers",
    "cmc_fetcher_helpers",
    "cmc_checker_helpers",
    "cmc_real_time_helpers",
}


def _collect_core_performance_metrics(context: CollectContext) -> Iterable[DumpItem]:
    result = livestatus.LocalConnection().query("GET status\nColumnHeaders: on")
    performance_data = {
        key: result[1][i]
        for i in range(len(result[0]))
        if (key := result[0][i]) not in ["license_usage_history"]
    }
    for key in _CMC_SETTING_KEYS.intersection(context.base_config):
        performance_data[key] = context.base_config[key]

    yield DumpItem(
        PurePosixPath("perfdata.json"),
        GeneratedContent(json.dumps(performance_data, sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_core_performance_metrics = DiagnosticsPlugin(
    name="core_performance_metrics",
    description=Help("Metrics related to sizing, e.g. number of helpers, hosts, services"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_PERFORMANCE,
    handler=_collect_core_performance_metrics,
)
