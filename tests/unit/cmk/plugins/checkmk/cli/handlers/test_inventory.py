#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.inventory import (
    _InventorizeMarkedHostsCommand,
    _InventoryCommand,
)
from cmk.plugins.checkmk.cli.inventory import InventorizeMarkedHostsRequest, InventoryRequest
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest

_OMD_ROOT = Path("/omd/sites/mysite")

_CONTEXT = CLIContext(
    omd_root=_OMD_ROOT,
    global_options=CLIGlobalOptions(),
    logger=logging.getLogger(__name__),
)

_FILE_CACHE = FileCacheRequest(cache=False, no_cache=False, no_tcp=False)

_REQUEST = InventoryRequest(
    file_cache=_FILE_CACHE,
    usewalk=False,
    snmp_backend=None,
    force=False,
    plugin_selection=PluginSelectionRequest(
        detect_sections=None, plugins=None, detect_plugins=None
    ),
    fake_dns=None,
    hosts=("myhost",),
)


class _FakeInventorize:
    def __init__(self, error: MKGeneralException | None = None) -> None:
        self.asked: list[tuple[InventoryRequest, Path, bool]] = []
        self._error = error

    def __call__(self, request: InventoryRequest, *, omd_root: Path, debug: bool) -> None:
        self.asked.append((request, omd_root, debug))
        if self._error is not None:
            raise self._error


def test_the_requested_hosts_are_inventorized() -> None:
    inventorize = _FakeInventorize()

    _InventoryCommand(inventorize=inventorize).run(_CONTEXT, _REQUEST)

    assert inventorize.asked == [(_REQUEST, _OMD_ROOT, False)]


def test_a_failed_inventory_exits_three() -> None:
    inventorize = _FakeInventorize(error=MKGeneralException("Cannot load the configuration"))

    assert _InventoryCommand(inventorize=inventorize).run(_CONTEXT, _REQUEST) == CLIExitCode.UNKNOWN


class _FakeInventorizeMarkedHosts:
    def __init__(self) -> None:
        self.asked: list[tuple[InventorizeMarkedHostsRequest, Path, bool]] = []

    def __call__(
        self, request: InventorizeMarkedHostsRequest, *, omd_root: Path, debug: bool
    ) -> None:
        self.asked.append((request, omd_root, debug))


def test_the_marked_hosts_are_inventorized() -> None:
    inventorize = _FakeInventorizeMarkedHosts()
    request = InventorizeMarkedHostsRequest(
        file_cache=_FILE_CACHE, usewalk=False, snmp_backend=None, fake_dns=None
    )

    _InventorizeMarkedHostsCommand(inventorize_marked_hosts=inventorize).run(_CONTEXT, request)

    assert inventorize.asked == [(request, _OMD_ROOT, False)]
