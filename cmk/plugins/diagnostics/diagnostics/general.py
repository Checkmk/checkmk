#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from datetime import datetime
from pathlib import PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_GENERAL


def _collect_parameters(context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("parameters_%s" % datetime.now().timestamp()),
        GeneratedContent(str(dict(context.all_parameters)).encode()),
    )


diagnostics_plugin_parameters = DiagnosticsPlugin(
    name="parameters",
    description=Help("The parameters this diagnostics dump was created with"),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_GENERAL,
    always=True,
    handler=_collect_parameters,
)
