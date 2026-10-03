#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The results of the diagnostics dump automations.

Both the automations, which produce them, and their callers use them.
"""

from dataclasses import dataclass
from typing import override

from cmk.automations.internal import AutomationID, AutomationResult


@dataclass
class CreateDiagnosticsDumpResult(AutomationResult):
    output: str
    tarfile_path: str
    tarfile_created: bool

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("create-diagnostics-dump")


@dataclass
class CreateDiagnosticsDumpV2Result(AutomationResult):
    output: str
    tarfile_path: str
    tarfile_created: bool

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("create-diagnostics-dump-v2")


__all__ = [
    "CreateDiagnosticsDumpResult",
    "CreateDiagnosticsDumpV2Result",
]
