#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.base.core.interface import CoreActivationError
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.core_config import CoreConfigRequest
from cmk.plugins.checkmk.cli.handlers.core_config import _ConfigureCoreCommand, _UpdateCommand

from ._context import context, OMD_ROOT

_REQUEST = CoreConfigRequest(fake_dns=None, hosts=(HostAddress("host1"),))

_FAILURE = MKGeneralException("Cannot load the configuration")


class _FakeConfigureCore:
    def __init__(self, error: Exception | None = None) -> None:
        self.asked: list[tuple[CoreConfigRequest, Path, bool]] = []
        self._error = error

    def __call__(self, request: CoreConfigRequest, *, omd_root: Path, debug: bool) -> None:
        self.asked.append((request, omd_root, debug))
        if self._error is not None:
            raise self._error


def test_the_core_is_configured_for_the_requested_hosts() -> None:
    configure_core = _FakeConfigureCore()

    _ConfigureCoreCommand(configure_core=configure_core).run(context(), _REQUEST)

    assert configure_core.asked == [(_REQUEST, OMD_ROOT, False)]


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(_FAILURE, id="config-not-loadable"),
        pytest.param(CoreActivationError("Cannot restart the core"), id="core-not-restartable"),
    ],
)
def test_a_failed_core_configuration_exits_three(error: Exception) -> None:
    assert (
        _ConfigureCoreCommand(configure_core=_FakeConfigureCore(error=error)).run(
            context(), _REQUEST
        )
        == CLIExitCode.UNKNOWN
    )


class _FakeUpdate:
    def __init__(self, *, updated: bool) -> None:
        self.asked: list[tuple[HostAddress | None, Path, bool]] = []
        self._updated = updated

    def __call__(self, fake_dns: HostAddress | None, *, omd_root: Path, debug: bool) -> bool:
        self.asked.append((fake_dns, omd_root, debug))
        return self._updated


def test_the_core_config_is_updated_with_the_fake_address() -> None:
    update = _FakeUpdate(updated=True)

    _UpdateCommand(update=update).run(context(), HostAddress("127.0.0.1"))

    assert update.asked == [(HostAddress("127.0.0.1"), OMD_ROOT, False)]


def test_a_configuration_error_exits_one() -> None:
    assert (
        _UpdateCommand(update=_FakeUpdate(updated=False)).run(context(), None)
        == CLIExitCode.FAILURE
    )
