#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.diagnostics.internal import (
    CollectContext,
    CollectInfo,
    DiagnosticsPlugin,
    DumpItem,
    Help,
    Sensitivity,
    Topic,
    VerbatimCopy,
)
from cmk.profiling.backend import (
    PROFILE_ID_RE,
    PROFILE_SUFFIXES,
    profiles_dir,
    PROFILES_RELATIVE_DIR,
)

# Shared with the diagnostics plugin family; topics compare by value.
_TOPIC_PERFORMANCE = Topic("Performance & sizing")


def _collect_gui_profiles(context: CollectContext) -> Iterable[DumpItem]:
    directory = profiles_dir(context.omd_root)
    packed = False
    if directory.is_dir():
        for source in sorted(directory.iterdir()):
            if not source.is_file() or source.suffix not in PROFILE_SUFFIXES:
                continue
            if not PROFILE_ID_RE.match(source.name.split(".", 1)[0]):
                continue
            packed = True
            yield DumpItem(PROFILES_RELATIVE_DIR / source.name, VerbatimCopy(source))
    if not packed:
        raise CollectInfo("No profiles found")


diagnostics_plugin_gui_profiles = DiagnosticsPlugin(
    name="gui_profiles",
    description=Help("Stored GUI performance profiles and flamegraphs"),
    sensitivity=Sensitivity.MEDIUM,
    topic=_TOPIC_PERFORMANCE,
    handler=_collect_gui_profiles,
)
