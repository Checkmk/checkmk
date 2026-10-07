#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from typing import override

import pytest

import cmk.ccc.resulttype as result
import cmk.utils.paths
from cmk.base.errorhandling import RecordingFetcher, serialize_fetched
from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetcher_abc import FetcherFunction
from cmk.checkengine.helper_interface import AgentRawData, FetcherType, SourceInfo, SourceType
from cmk.checkengine.snmplib import SNMPRawData, SNMPSectionMarker
from cmk.piggyback.backend import store_piggyback_raw_data

type _Fetched = list[tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception]]]


def _source(
    fetcher_type: FetcherType, ident: str, ipaddress: HostAddress | None = None
) -> SourceInfo:
    return SourceInfo(
        hostname=HostName("myhost"),
        ipaddress=ipaddress,
        ident=ident,
        fetcher_type=fetcher_type,
        source_type=SourceType.HOST,
    )


def test_each_source_is_preceded_by_a_separator() -> None:
    fetched: _Fetched = [
        (_source(FetcherType.TCP, "agent"), result.OK(AgentRawData(b"<<<a>>>\n1\n"))),
        (_source(FetcherType.SPECIAL_AGENT, "special_foo"), result.OK(AgentRawData(b"<<<b>>>\n2"))),
    ]

    serialized = serialize_fetched(fetched)

    assert serialized == (
        b"===== myhost agent (TCP) =====\n<<<a>>>\n1\n"
        b"===== myhost special_foo (SPECIAL_AGENT) =====\n<<<b>>>\n2\n"
    )


def test_snmp_data_is_serialized_as_a_python_literal() -> None:
    snmp_data: SNMPRawData = {SNMPSectionMarker("uptime"): [[["123"]]]}

    serialized = serialize_fetched([(_source(FetcherType.SNMP, "snmp"), result.OK(snmp_data))])

    assert serialized is not None
    header, payload = serialized.split(b"\n", 1)
    assert header == b"===== myhost snmp (SNMP) ====="
    assert ast.literal_eval(payload.decode()) == {"uptime": [[["123"]]]}


def test_failed_sources_are_left_out() -> None:
    fetched: _Fetched = [
        (_source(FetcherType.TCP, "agent"), result.Error(Exception("connection refused"))),
        (_source(FetcherType.SPECIAL_AGENT, "special_foo"), result.OK(AgentRawData(b"<<<b>>>\n"))),
    ]

    serialized = serialize_fetched(fetched)

    assert serialized == b"===== myhost special_foo (SPECIAL_AGENT) =====\n<<<b>>>\n"


def test_stored_piggyback_messages_are_included() -> None:
    store_piggyback_raw_data(
        HostName("source_host"),
        {HostName("myhost"): [b"<<<lnx_thermal>>>", b"Zone 0"]},
        message_timestamp=1791391767.0,
        contact_timestamp=1791391767.0,
        omd_root=cmk.utils.paths.omd_root,
    )

    serialized = serialize_fetched(
        [(_source(FetcherType.PIGGYBACK, "piggyback"), result.OK(AgentRawData(b"")))]
    )

    assert serialized == (
        b"===== myhost piggyback (PIGGYBACK) =====\n"
        b"===== myhost piggyback (PIGGYBACK) from source_host,"
        b" last update 2026-10-07T16:49:27+00:00 =====\n"
        b"<<<lnx_thermal>>>\nZone 0\n"
    )


def test_piggyback_messages_stored_for_the_ip_address_are_included() -> None:
    store_piggyback_raw_data(
        HostName("source_host"),
        {HostName("10.0.0.1"): [b"<<<lnx_thermal>>>", b"Zone 0"]},
        message_timestamp=1791391767.0,
        contact_timestamp=1791391767.0,
        omd_root=cmk.utils.paths.omd_root,
    )

    serialized = serialize_fetched(
        [
            (
                _source(FetcherType.PIGGYBACK, "piggyback", HostAddress("10.0.0.1")),
                result.OK(AgentRawData(b"")),
            )
        ]
    )

    assert serialized == (
        b"===== myhost piggyback (PIGGYBACK) =====\n"
        b"===== myhost piggyback (PIGGYBACK) from source_host,"
        b" last update 2026-10-07T16:49:27+00:00 =====\n"
        b"<<<lnx_thermal>>>\nZone 0\n"
    )


def test_nothing_fetched_serializes_to_none() -> None:
    fetched: _Fetched = [(_source(FetcherType.TCP, "agent"), result.Error(Exception("timeout")))]

    assert serialize_fetched(fetched) is None


class _AgentFetcher(FetcherFunction):
    @override
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        source = SourceInfo(
            hostname=host_name,
            ipaddress=ip_address,
            ident="agent",
            fetcher_type=FetcherType.TCP,
            source_type=SourceType.HOST,
        )
        return [(source, result.OK(AgentRawData(b"<<<a>>>\n")), Snapshot.null())]


def test_recording_fetcher_serializes_the_data_fetched_for_the_host() -> None:
    fetcher = RecordingFetcher(_AgentFetcher())
    fetcher(HostName("myhost"), ip_address=None)

    assert fetcher.serialized(HostName("myhost")) == b"===== myhost agent (TCP) =====\n<<<a>>>\n"


def test_recording_fetcher_has_nothing_for_another_host() -> None:
    fetcher = RecordingFetcher(_AgentFetcher())
    fetcher(HostName("myhost"), ip_address=None)

    assert fetcher.serialized(HostName("otherhost")) is None


class _FailsOnSecondCall(_AgentFetcher):
    def __init__(self) -> None:
        self._called = False

    @override
    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[SourceInfo, result.Result[AgentRawData | SNMPRawData, Exception], Snapshot]
    ]:
        if self._called:
            raise RuntimeError("fetching failed")
        self._called = True
        return super().__call__(host_name, ip_address=ip_address)


def test_recording_fetcher_has_nothing_after_a_failed_fetch() -> None:
    fetcher = RecordingFetcher(_FailsOnSecondCall())
    fetcher(HostName("myhost"), ip_address=None)

    with pytest.raises(RuntimeError):
        fetcher(HostName("myhost"), ip_address=None)

    assert fetcher.serialized(HostName("myhost")) is None
