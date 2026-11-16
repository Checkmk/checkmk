#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmplib import OID, SNMPBackendEnum
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.options import FAKE_DNS_VALUE, SNMP_BACKEND_VALUE
from cmk.plugins.checkmk.cli.snmp import (
    _EXTRA_OIDS_VALUES,
    _get_request,
    _OIDS_VALUES,
    _translate_request,
    _walk_request,
    GetRequest,
    WalkRequest,
)


def test_the_walk_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        SNMP_BACKEND_VALUE: ["classic"],
        FAKE_DNS_VALUE: ["1.2.3.4"],
        _EXTRA_OIDS_VALUES: [".1.2"],
        _OIDS_VALUES: [".1.3", ".1.4"],
        CLIArguments(placeholder="HOST1 HOST2...", parse=HostName): ["host1", "host2"],
    }

    assert _walk_request(CLIReader(lambda declaration: given.get(declaration, ()))) == WalkRequest(
        backend=SNMPBackendEnum.CLASSIC,
        extra_oids=(".1.2",),
        oids=(".1.3", ".1.4"),
        fake_dns=HostAddress("1.2.3.4"),
        hosts=(HostName("host1"), HostName("host2")),
    )


def test_the_get_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        SNMP_BACKEND_VALUE: ["stored-walk"],
        CLIArgument(placeholder="OID", parse=OID): [".1.3.6"],
        CLIArguments(placeholder="HOST1 HOST2...", parse=HostName): ["host1"],
    }

    assert _get_request(CLIReader(lambda declaration: given.get(declaration, ()))) == GetRequest(
        backend=SNMPBackendEnum.STORED_WALK,
        fake_dns=None,
        oid=".1.3.6",
        hosts=(HostName("host1"),),
    )


def test_the_walk_to_translate_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        CLIArgument(placeholder="WALK", parse=str): ["myhost"]
    }

    assert _translate_request(CLIReader(lambda declaration: given.get(declaration, ()))) == "myhost"


def test_an_invalid_host_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a host"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {
            CLIArguments(placeholder="HOST1 HOST2...", parse=HostName): ["not a host"]
        }

        _walk_request(CLIReader(lambda declaration: given.get(declaration, ())))


def test_an_unknown_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="bogus"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {SNMP_BACKEND_VALUE: ["bogus"]}

        _get_request(CLIReader(lambda declaration: given.get(declaration, ())))


def test_an_invalid_fake_address_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid host address"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {FAKE_DNS_VALUE: ["not an address"]}

        _walk_request(CLIReader(lambda declaration: given.get(declaration, ())))
