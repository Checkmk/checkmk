#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from collections.abc import Iterable
from pathlib import PurePosixPath

from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.topics import TOPIC_OPERATING_SYSTEM


def _collect_environment_variables(_context: CollectContext) -> Iterable[DumpItem]:
    yield DumpItem(
        PurePosixPath("environment.json"),
        GeneratedContent(json.dumps(dict(os.environ), sort_keys=True, indent=4).encode()),
    )


diagnostics_plugin_environment_variables = DiagnosticsPlugin(
    name="environment_variables",
    description=Help("The environment variables of the site user"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_OPERATING_SYSTEM,
    handler=_collect_environment_variables,
)
