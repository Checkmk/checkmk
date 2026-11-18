#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.base.config import HostSelectionError
from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.handlers.agent_based import PluginSelectionError
from cmk.plugins.checkmk.cli.handlers.inventory import (
    _InventorizeMarkedHostsCommand,
    _InventoryCommand,
)
from cmk.plugins.checkmk.cli.inventory import InventoryRequest
from cmk.plugins.checkmk.cli.options import FetchRequest, FileCacheRequest, PluginSelectionRequest

from ._context import context, OMD_ROOT

_FILE_CACHE = FileCacheRequest(cache=False, no_cache=False, no_tcp=False)

_REQUEST = InventoryRequest(
    fetch=FetchRequest(file_cache=_FILE_CACHE, usewalk=False, snmp_backend=None, fake_dns=None),
    force=False,
    plugin_selection=PluginSelectionRequest(
        detect_sections=None, plugins=None, detect_plugins=None
    ),
    hosts=("myhost",),
)


class _FakeInventorize:
    def __init__(self, error: Exception | None = None) -> None:
        self.asked: list[tuple[InventoryRequest, Path, bool]] = []
        self._error = error

    def __call__(self, request: InventoryRequest, *, omd_root: Path, debug: bool) -> None:
        self.asked.append((request, omd_root, debug))
        if self._error is not None:
            raise self._error


def test_the_requested_hosts_are_inventorized() -> None:
    inventorize = _FakeInventorize()

    _InventoryCommand(inventorize=inventorize).run(context(), _REQUEST)

    assert inventorize.asked == [(_REQUEST, OMD_ROOT, False)]


@pytest.mark.parametrize(
    "error",
    [
        MKGeneralException("Cannot load the configuration"),
        HostSelectionError("No such host"),
        PluginSelectionError("Unknown plug-in"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_a_failed_inventory_exits_three(error: Exception) -> None:
    inventorize = _FakeInventorize(error=error)

    assert (
        _InventoryCommand(inventorize=inventorize).run(context(), _REQUEST) == CLIExitCode.UNKNOWN
    )


class _FakeInventorizeMarkedHosts:
    def __init__(self) -> None:
        self.asked: list[tuple[FetchRequest, Path, bool]] = []

    def __call__(self, request: FetchRequest, *, omd_root: Path, debug: bool) -> None:
        self.asked.append((request, omd_root, debug))


def test_the_marked_hosts_are_inventorized() -> None:
    inventorize = _FakeInventorizeMarkedHosts()
    request = FetchRequest(file_cache=_FILE_CACHE, usewalk=False, snmp_backend=None, fake_dns=None)

    _InventorizeMarkedHostsCommand(inventorize_marked_hosts=inventorize).run(context(), request)

    assert inventorize.asked == [(request, OMD_ROOT, False)]
