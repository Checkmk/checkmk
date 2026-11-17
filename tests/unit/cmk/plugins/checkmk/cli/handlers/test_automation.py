#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import override

import pytest

from cmk.automations.engine import AutomationError
from cmk.automations.internal import AutomationID, AutomationResult
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.automation import AutomationRequest
from cmk.plugins.checkmk.cli.handlers.automation import (
    _automation_error_exit_code,
    _AutomationCommand,
)

_OMD_ROOT = Path("/omd/sites/mysite")


@dataclass
class _Result(AutomationResult):
    value: str

    @override
    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("test")


class _FakeExecuteAutomation:
    def __init__(self, result: AutomationResult | AutomationError = _Result("done")) -> None:
        self.executed: list[tuple[AutomationID, list[str], Path, bool]] = []
        self._result = result

    def __call__(
        self, name: AutomationID, args: list[str], *, omd_root: Path, debug: bool
    ) -> AutomationResult | AutomationError:
        self.executed.append((name, args, omd_root, debug))
        return self._result


def _context() -> CLIContext:
    return CLIContext(
        omd_root=_OMD_ROOT,
        global_options=CLIGlobalOptions(),
        logger=logging.getLogger(__name__),
    )


def _request(*arguments: str) -> AutomationRequest:
    return AutomationRequest(for_cmk_version=None, arguments=arguments)


@pytest.mark.parametrize(
    ["error", "expected"],
    [
        (AutomationError.KNOWN_ERROR, CLIExitCode.FAILURE),
        (AutomationError.UNKNOWN_ERROR, CLIExitCode.ERROR),
    ],
)
def test_an_automation_error_exits_with_its_value(
    error: AutomationError, expected: CLIExitCode
) -> None:
    assert _automation_error_exit_code(error) == expected


def test_the_named_automation_runs_with_its_arguments() -> None:
    execute = _FakeExecuteAutomation()

    _AutomationCommand(execute=execute).run(
        _context(), _request("service-discovery-preview", "myhost"), ()
    )

    assert execute.executed == [
        (AutomationID("service-discovery-preview"), ["myhost"], _OMD_ROOT, False)
    ]


def test_an_automation_without_name_exits_three() -> None:
    assert _AutomationCommand(execute=_FakeExecuteAutomation()).run(_context(), _request(), ()) == (
        CLIExitCode.UNKNOWN
    )


def test_the_result_is_written_serialized(capsys: pytest.CaptureFixture[str]) -> None:

    _AutomationCommand(execute=_FakeExecuteAutomation()).run(_context(), _request("test"), ())

    assert capsys.readouterr().out == "('done',)\n"


def test_a_failed_automation_exits_with_its_error() -> None:
    execute = _FakeExecuteAutomation(AutomationError.UNKNOWN_ERROR)

    assert (
        _AutomationCommand(execute=execute).run(_context(), _request("test"), ())
        == CLIExitCode.ERROR
    )
