#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmplib import OID
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.checkmk.cli.handlers.snmp import (
    _OIDValue,
    _SNMPGetCommand,
    _SNMPTranslateCommand,
    _SNMPWalkCommand,
)
from cmk.plugins.checkmk.cli.snmp import GetRequest, WalkRequest


def _context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )


class _FakeTranslateWalk:
    def __init__(
        self,
        translated: Sequence[tuple[bytes, bytes]] = (),
        error: MKGeneralException | None = None,
    ) -> None:
        self.asked: list[str] = []
        self._translated = translated
        self._error = error

    def __call__(self, walk_name: str) -> Sequence[tuple[bytes, bytes]]:
        self.asked.append(walk_name)
        if self._error is not None:
            raise self._error
        return self._translated


def test_an_empty_walk_name_exits_three() -> None:
    assert (
        _SNMPTranslateCommand(translate_walk=_FakeTranslateWalk()).run(_context(), "")
        == CLIExitCode.UNKNOWN
    )


def test_an_empty_walk_name_is_not_translated() -> None:
    translate = _FakeTranslateWalk()

    _SNMPTranslateCommand(translate_walk=translate).run(_context(), "")

    assert translate.asked == []


def test_the_named_walk_is_translated() -> None:
    translate = _FakeTranslateWalk()

    _SNMPTranslateCommand(translate_walk=translate).run(_context(), "myhost")

    assert translate.asked == ["myhost"]


def test_a_walk_that_cannot_be_translated_exits_three() -> None:
    translate = _FakeTranslateWalk(error=MKGeneralException("The walk does not exist"))

    assert (
        _SNMPTranslateCommand(translate_walk=translate).run(_context(), "myhost")
        == CLIExitCode.UNKNOWN
    )


def test_a_walk_that_cannot_be_translated_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    translate = _FakeTranslateWalk(error=MKGeneralException("The walk does not exist"))

    with caplog.at_level(logging.ERROR):
        _SNMPTranslateCommand(translate_walk=translate).run(_context(), "myhost")

    assert caplog.messages == ["The walk does not exist"]


def test_a_walk_that_cannot_be_translated_is_raised_through_under_debug() -> None:
    translate = _FakeTranslateWalk(error=MKGeneralException("The walk does not exist"))

    with pytest.raises(MKGeneralException, match="The walk does not exist"):
        _SNMPTranslateCommand(translate_walk=translate).run(_context(debug=True), "myhost")


def test_the_translated_walk_is_written(capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    translate = _FakeTranslateWalk([(b".1.3.6.1 value ", b" SNMPv2-SMI::internet\n")])

    _SNMPTranslateCommand(translate_walk=translate).run(_context(), "myhost")

    assert capsysbinary.readouterr().out == b".1.3.6.1 value --> SNMPv2-SMI::internet\n"


def test_a_value_that_is_no_utf8_is_written_as_is(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    translate = _FakeTranslateWalk([(b'.1.3.6.1 "\xff"', b"SNMPv2-SMI::internet")])

    _SNMPTranslateCommand(translate_walk=translate).run(_context(), "myhost")

    assert capsysbinary.readouterr().out == b'.1.3.6.1 "\xff" --> SNMPv2-SMI::internet\n'


class _FakeWalkHosts:
    def __init__(self, error: MKGeneralException | None = None) -> None:
        self.walked: list[tuple[WalkRequest, bool]] = []
        self._error = error

    def __call__(self, request: WalkRequest, *, debug: bool) -> None:
        self.walked.append((request, debug))
        if self._error is not None:
            raise self._error


def _walk_request(
    *,
    hosts: Sequence[HostName] = (HostName("myhost"),),
    oids: Sequence[OID] = (),
    extra_oids: Sequence[OID] = (),
) -> WalkRequest:
    return WalkRequest(
        backend=None,
        extra_oids=extra_oids,
        oids=oids,
        fake_dns=None,
        hosts=hosts,
    )


def test_oids_and_extra_oids_together_exit_three() -> None:
    request = _walk_request(oids=(".1.3",), extra_oids=(".1.4",))

    assert (
        _SNMPWalkCommand(walk_hosts=_FakeWalkHosts()).run(_context(), request)
        == CLIExitCode.UNKNOWN
    )


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        _SNMPWalkCommand(walk_hosts=_FakeWalkHosts()).run(
            _context(debug=True), _walk_request(oids=(".1.3",), extra_oids=(".1.4",))
        )


def test_a_walk_without_hosts_exits_three() -> None:
    request = _walk_request(hosts=())

    assert (
        _SNMPWalkCommand(walk_hosts=_FakeWalkHosts()).run(_context(), request)
        == CLIExitCode.UNKNOWN
    )


def test_the_requested_hosts_are_walked() -> None:
    walk_hosts = _FakeWalkHosts()

    _SNMPWalkCommand(walk_hosts=walk_hosts).run(_context(), _walk_request())

    assert walk_hosts.walked == [(_walk_request(), False)]


def test_a_failed_walk_exits_three() -> None:
    walk_hosts = _FakeWalkHosts(error=MKGeneralException("Failed to gather IP address"))

    assert (
        _SNMPWalkCommand(walk_hosts=walk_hosts).run(_context(), _walk_request())
        == CLIExitCode.UNKNOWN
    )


class _FakeGetOIDValues:
    def __init__(
        self, values: Sequence[_OIDValue], error: MKGeneralException | None = None
    ) -> None:
        self.asked: list[tuple[OID, GetRequest, bool]] = []
        self._values = values
        self._error = error

    def __call__(self, oid: OID, request: GetRequest, *, debug: bool) -> Iterator[_OIDValue]:
        self.asked.append((oid, request, debug))
        yield from self._values
        if self._error is not None:
            raise self._error


_VALUE = _OIDValue(HostName("myhost"), HostAddress("1.2.3.4"), "Linux")


def _get_request() -> GetRequest:
    return GetRequest(backend=None, fake_dns=None, oid=".1.3.6.1.2.1.1.1.0", hosts=())


def test_the_requested_oid_is_got() -> None:
    get_values = _FakeGetOIDValues([])

    _SNMPGetCommand(get_oid_values=get_values).run(_context(), _get_request())

    assert get_values.asked == [(".1.3.6.1.2.1.1.1.0", _get_request(), False)]


def test_each_value_is_written_with_its_host(capsys: pytest.CaptureFixture[str]) -> None:

    _SNMPGetCommand(get_oid_values=_FakeGetOIDValues([_VALUE])).run(_context(), _get_request())

    assert capsys.readouterr().out == "myhost (1.2.3.4): 'Linux'\n"


def test_the_values_got_before_a_failure_are_written(capsys: pytest.CaptureFixture[str]) -> None:
    get_values = _FakeGetOIDValues([_VALUE], error=MKGeneralException("No-IP host"))

    _SNMPGetCommand(get_oid_values=get_values).run(_context(), _get_request())

    assert capsys.readouterr().out == "myhost (1.2.3.4): 'Linux'\n"


def test_a_failed_get_exits_three() -> None:
    get_values = _FakeGetOIDValues([], error=MKGeneralException("No-IP host"))

    assert (
        _SNMPGetCommand(get_oid_values=get_values).run(_context(), _get_request())
        == CLIExitCode.UNKNOWN
    )
