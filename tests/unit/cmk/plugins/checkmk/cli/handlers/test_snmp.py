#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.snmplib import OID
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.snmp import (
    cli_handler_snmptranslate,
    cli_handler_snmpwalk,
)
from cmk.plugins.checkmk.cli.snmp import WalkRequest


def _context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )


def test_an_empty_walk_name_exits_three() -> None:
    assert cli_handler_snmptranslate.run(_context(), "", ()) == CLIExitCode.UNKNOWN


def test_an_empty_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        cli_handler_snmptranslate.run(_context(), "", ())

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_an_empty_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        cli_handler_snmptranslate.run(_context(debug=True), "", ())


def _walk_request(
    *hosts: HostName, oids: tuple[OID, ...] = (), extra_oids: tuple[OID, ...] = ()
) -> WalkRequest:
    return WalkRequest(backend=None, extra_oids=extra_oids, oids=oids, fake_dns=None, hosts=hosts)


def test_oids_and_extra_oids_together_exit_three() -> None:
    request = _walk_request(HostName("myhost"), oids=("1.3",), extra_oids=("1.4",))

    assert cli_handler_snmpwalk.run(_context(), request, ()) == CLIExitCode.UNKNOWN


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    request = _walk_request(HostName("myhost"), oids=("1.3",), extra_oids=("1.4",))

    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        cli_handler_snmpwalk.run(_context(debug=True), request, ())


def test_a_walk_without_hosts_exits_three() -> None:
    assert cli_handler_snmpwalk.run(_context(), _walk_request(), ()) == CLIExitCode.UNKNOWN
