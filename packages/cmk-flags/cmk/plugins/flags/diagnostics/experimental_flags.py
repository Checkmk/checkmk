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
    Topic,
    VerbatimCopy,
)
from cmk.flags import CONFIG_FILENAME, STAGED_CONFIG_FILENAME

# Shared with the diagnostics plugin family; topics compare by value.
_TOPIC_GENERAL = Topic("General site information")

_CONFIG_DIR = PurePosixPath("etc/check_mk")


def _collect_experimental_flags(context: CollectContext) -> Iterable[DumpItem]:
    for name in (CONFIG_FILENAME, STAGED_CONFIG_FILENAME):
        source = context.omd_root / _CONFIG_DIR / name
        if source.is_file():
            yield DumpItem(_CONFIG_DIR / name, VerbatimCopy(source))


diagnostics_plugin_experimental_flags = DiagnosticsPlugin(
    name="experimental_flags",
    description=Help("The active and the staged experimental flags"),
    sensitivity=Sensitivity.LOW,
    topic=_TOPIC_GENERAL,
    always=True,
    handler=_collect_experimental_flags,
)
