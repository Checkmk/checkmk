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
    CollectInfo,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
    VerbatimCopy,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_PERFORMANCE
from cmk.profiling.backend import PROFILE_ID_RE, PROFILE_SUFFIXES


def _collect_core_performance_metrics(context: CollectContext) -> Iterable[DumpItem]:
    result = livestatus.LocalConnection().query("GET status\nColumnHeaders: on")
    performance_data = {
        key: result[1][i]
        for i in range(len(result[0]))
        if (key := result[0][i]) not in ["license_usage_history"]
    }
    performance_data.update(context.core_performance_settings)
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
_PROFILES_REL_DIR = PurePosixPath("var/check_mk/profiles")


def _collect_gui_profiles(context: CollectContext) -> Iterable[DumpItem]:
    profiles_dir = context.omd_root / "var/check_mk/profiles"
    packed = False
    if profiles_dir.is_dir():
        for source in sorted(profiles_dir.iterdir()):
            if not source.is_file() or source.suffix not in PROFILE_SUFFIXES:
                continue
            if not PROFILE_ID_RE.match(source.name.split(".", 1)[0]):
                continue
            packed = True
            yield DumpItem(_PROFILES_REL_DIR / source.name, VerbatimCopy(source))
    if not packed:
        raise CollectInfo("No profiles found")


diagnostics_plugin_gui_profiles = DiagnosticsPlugin(
    name="gui_profiles",
    description=Help("Stored GUI performance profiles and flamegraphs"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_PERFORMANCE,
    handler=_collect_gui_profiles,
)
