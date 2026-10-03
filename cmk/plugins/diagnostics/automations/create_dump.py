#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The diagnostics dump automations.

The dump itself is built by cmk.base.diagnostics; these only run it on request
and report where it went.
"""

import io
from collections.abc import Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from typing import override

import cmk.utils.paths
from cmk.automations.internal import Automation, AutomationID, AutomationState
from cmk.base.diagnostics import (
    create_diagnostics_dump,
    create_diagnostics_dump_v2,
    deserialize_cl_parameters,
    DiagnosticsCLParameters,
)
from cmk.diagnostics.automation_types import (
    CreateDiagnosticsDumpResult,
    CreateDiagnosticsDumpV2Result,
)
from cmk.diagnostics.engine import DumpSelection
from cmk.utils import log


class RawConfigState(AutomationState):
    def __init__(self, _omd_root: object, raw_config: Mapping[str, object]) -> None:
        self._raw_config = raw_config

    @override
    def update(self, _omd_root: object, raw_config: Mapping[str, object]) -> None:
        self._raw_config = raw_config

    @property
    def raw_config(self) -> Mapping[str, object]:
        return self._raw_config


def handler(
    state: RawConfigState,
    args: DiagnosticsCLParameters,
) -> CreateDiagnosticsDumpResult:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()
        dump = create_diagnostics_dump(
            omd_root=cmk.utils.paths.omd_root,
            diagnostics_dir=cmk.utils.paths.diagnostics_dir,
            parameters=deserialize_cl_parameters(args),
            raw_config=state.raw_config,
        )
        return CreateDiagnosticsDumpResult(
            output=buf.getvalue(),
            tarfile_path=str(dump.tarfile_path),
            tarfile_created=dump.tarfile_created,
        )


automation_create_diagnostics_dump = Automation(
    name=AutomationID("create-diagnostics-dump"),
    state_factory=RawConfigState,
    handler=handler,
    result=CreateDiagnosticsDumpResult,
)


def handler_v2(
    state: RawConfigState,
    args: Sequence[str],
) -> CreateDiagnosticsDumpV2Result:
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        log.setup_console_logging()
        dump = create_diagnostics_dump_v2(
            omd_root=cmk.utils.paths.omd_root,
            diagnostics_dir=cmk.utils.paths.diagnostics_dir,
            selection=(DumpSelection.deserialize(args[0]) if args else DumpSelection(plugins=())),
            raw_config=state.raw_config,
        )
        return CreateDiagnosticsDumpV2Result(
            output=buf.getvalue(),
            tarfile_path=str(dump.tarfile_path),
            tarfile_created=dump.tarfile_created,
        )


automation_create_diagnostics_dump_v2 = Automation(
    name=AutomationID("create-diagnostics-dump-v2"),
    state_factory=RawConfigState,
    handler=handler_v2,
    result=CreateDiagnosticsDumpV2Result,
)
