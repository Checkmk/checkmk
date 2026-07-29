#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import PurePosixPath

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
from cmk.profiling.backend import PROFILE_ID_RE, PROFILE_SUFFIXES

# Shared with the diagnostics plugin family; topics compare by value.
_TOPIC_PERFORMANCE = Topic("Performance & sizing")

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
    topic=_TOPIC_PERFORMANCE,
    handler=_collect_gui_profiles,
)
