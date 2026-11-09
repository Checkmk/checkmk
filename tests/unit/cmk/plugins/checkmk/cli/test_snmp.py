#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.cli.engine.commands import bind as cli_bind
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.snmp import (
    _get_request,
    _GetRequest,
    _walk_request,
    _WalkRequest,
    cli_command_snmpget,
    cli_command_snmptranslate,
    cli_command_snmpwalk,
)


def _context(*, debug_mode: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(debug=debug_mode),
        logger=logging.getLogger(__name__),
    )


def _run[R](
    command: CLICommand[R],
    options: list[tuple[str, str]],
    args: CLIArgs,
    *,
    debug_mode: bool = False,
) -> CLIExitCode:
    bound = cli_bind(command, CLIParsedOptions(options, logging.getLogger(__name__)))
    return bound(_context(debug_mode=debug_mode), args)


def test_a_missing_walk_name_exits_three() -> None:
    assert _run(cli_command_snmptranslate, [], [""]) == CLIExitCode.UNKNOWN


def test_a_missing_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _run(cli_command_snmptranslate, [], [""])

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_a_missing_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        _run(cli_command_snmptranslate, [], [""], debug_mode=True)


def test_oids_and_extra_oids_together_exit_three() -> None:
    assert (
        _run(cli_command_snmpwalk, [("--oid", "1.3"), ("--extraoid", "1.4")], [])
        == CLIExitCode.UNKNOWN
    )


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        _run(cli_command_snmpwalk, [("--oid", "1.3"), ("--extraoid", "1.4")], [], debug_mode=True)


def _declared[R](command: CLICommand[R]) -> list[str]:
    recorded = CLIRecordedOptions()
    command.request(recorded)
    return [option.long for option in recorded.options]


def test_snmpwalk_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_snmpwalk) == ["snmp-backend", "extraoid", "oid", "fake-dns"]


def test_snmpget_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_snmpget) == ["snmp-backend", "fake-dns"]


def test_snmptranslate_declares_no_options() -> None:
    assert _declared(cli_command_snmptranslate) == []


def test_the_walk_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions(
        [
            ("--snmp-backend", "classic"),
            ("--oid", ".1.3"),
            ("--oid", ".1.4"),
            ("--fake-dns", "1.2.3.4"),
        ],
        logging.getLogger(__name__),
    )

    assert _walk_request(options) == _WalkRequest(
        backend=SNMPBackendEnum.CLASSIC,
        extra_oids=(),
        oids=(".1.3", ".1.4"),
        fake_dns=HostAddress("1.2.3.4"),
    )


def test_the_get_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions([("--snmp-backend", "stored-walk")], logging.getLogger(__name__))

    assert _get_request(options) == _GetRequest(backend=SNMPBackendEnum.STORED_WALK, fake_dns=None)


def test_an_unknown_backend_is_rejected_before_the_command_runs() -> None:
    with pytest.raises(ValueError, match="--snmp-backend: Invalid argument"):
        cli_bind(
            cli_command_snmpget,
            CLIParsedOptions([("--snmp-backend", "bogus")], logging.getLogger(__name__)),
        )


def test_an_invalid_fake_address_is_rejected_before_the_command_runs() -> None:
    with pytest.raises(ValueError, match="--fake-dns: Invalid argument"):
        cli_bind(
            cli_command_snmpwalk,
            CLIParsedOptions([("--fake-dns", "not an address")], logging.getLogger(__name__)),
        )
