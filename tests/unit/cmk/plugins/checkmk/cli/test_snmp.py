#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.options import FAKE_DNS_VALUE, SNMP_BACKEND_VALUE
from cmk.plugins.checkmk.cli.snmp import (
    _EXTRA_OIDS_VALUES,
    _get_request,
    _GetRequest,
    _OIDS_VALUES,
    _run_snmptranslate,
    _run_snmpwalk,
    _walk_request,
    _WalkRequest,
)


def _context(*, debug_mode: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(debug=debug_mode),
        logger=logging.getLogger(__name__),
    )


def test_a_missing_walk_name_exits_three() -> None:
    assert _run_snmptranslate(_context(), None, [""]) == CLIExitCode.UNKNOWN


def test_a_missing_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _run_snmptranslate(_context(), None, [""])

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_a_missing_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        _run_snmptranslate(_context(debug_mode=True), None, [""])


def test_oids_and_extra_oids_together_exit_three() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _OIDS_VALUES: ["1.3"],
        _EXTRA_OIDS_VALUES: ["1.4"],
    }

    assert (
        _run_snmpwalk(
            _context(),
            _walk_request(CLIReader(lambda declaration: given.get(declaration, ()))),
            [],
        )
        == CLIExitCode.UNKNOWN
    )


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {
            _OIDS_VALUES: ["1.3"],
            _EXTRA_OIDS_VALUES: ["1.4"],
        }

        _run_snmpwalk(
            _context(debug_mode=True),
            _walk_request(CLIReader(lambda declaration: given.get(declaration, ()))),
            [],
        )


def test_the_walk_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        SNMP_BACKEND_VALUE: ["classic"],
        FAKE_DNS_VALUE: ["1.2.3.4"],
        _OIDS_VALUES: [".1.3", ".1.4"],
    }

    assert _walk_request(CLIReader(lambda declaration: given.get(declaration, ()))) == _WalkRequest(
        backend=SNMPBackendEnum.CLASSIC,
        extra_oids=(),
        oids=(".1.3", ".1.4"),
        fake_dns=HostAddress("1.2.3.4"),
    )


def test_the_get_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {SNMP_BACKEND_VALUE: ["stored-walk"]}

    assert _get_request(CLIReader(lambda declaration: given.get(declaration, ()))) == _GetRequest(
        backend=SNMPBackendEnum.STORED_WALK, fake_dns=None
    )


def test_an_unknown_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="bogus"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {SNMP_BACKEND_VALUE: ["bogus"]}

        _get_request(CLIReader(lambda declaration: given.get(declaration, ())))


def test_an_invalid_fake_address_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid host address"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {FAKE_DNS_VALUE: ["not an address"]}

        _walk_request(CLIReader(lambda declaration: given.get(declaration, ())))
