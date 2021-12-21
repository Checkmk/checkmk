#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
from itertools import repeat
from typing import Sequence

import pyghmi.exceptions  # type: ignore[import]
import pytest

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import (
    MKBailOut,
    MKException,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTerminate,
    MKTimeout,
)
from cmk.utils.type_defs import AgentRawData, result, SectionName

from cmk.snmplib.type_defs import SNMPRawData, SNMPTable

from cmk.core_helpers import FetcherType
from cmk.core_helpers.protocol import (
    AgentResultMessage,
    CMCHeader,
    CMCLogging,
    CMCLogLevel,
    CMCMessage,
    CMCResults,
    ErrorResultMessage,
    FetcherHeader,
    FetcherMessage,
    FetcherResultsStats,
    PayloadType,
    ResultStats,
    SNMPResultMessage,
)


class TestCMCLogLevel:
    def test_from_level(self):
        assert CMCLogLevel.from_level(logging.WARNING) is CMCLogLevel.WARNING


class TestCMCHeader:
    @pytest.mark.parametrize("state", [CMCHeader.State.RESULT, "RESULT "])
    def test_result_header(self, state):
        header = CMCHeader("name", state, "crit", 41)
        assert header == b"name :RESULT :crit    :41      :"

    @pytest.mark.parametrize("state", [CMCHeader.State.LOG, "LOG    "])
    def test_log_header(self, state):
        header = CMCHeader("fetch", state, "crit", 42)
        assert header == b"fetch:LOG    :crit    :42      :"

    def test_from_bytes(self):
        header = CMCHeader("fetch", "RESULT ", "crit", 42)
        assert CMCHeader.from_bytes(bytes(header) + 42 * b"*") == header

    def test_clone(self):
        header = CMCHeader("name", CMCHeader.State.RESULT, "crit", 42)
        other = header.clone()
        assert other is not header
        assert other == header

    def test_eq(self):
        header = CMCHeader("name", CMCHeader.State.RESULT, "crit", 42)
        assert header == bytes(header)
        assert bytes(header) == header

    def test_neq(self):
        header = CMCHeader("name", CMCHeader.State.RESULT, "crit", 42)

        other_name = header.clone()
        other_name.name = "toto"
        assert header != other_name

        other_state = header.clone()
        other_state.state = CMCHeader.State.LOG
        assert header != other_state

        other_crit = header.clone()
        other_crit.log_level = "tnih"
        assert header != other_crit

        other_len = header.clone()
        other_len.payload_length = 69
        assert header != other_len

    def test_repr(self):
        header = CMCHeader("name", "RESULT ", "crit", 42)
        assert isinstance(repr(header), str)

    def test_hash(self):
        header = CMCHeader("name", "RESULT ", "crit", 42)
        assert hash(header) == hash(bytes(header))

    def test_len(self):
        header = CMCHeader("name", "RESULT ", "crit", 42)
        assert len(header) == len(bytes(header))

    def test_critical_constants(self):
        """ATTENTION: Changing of those constants may require changing of C++ code"""
        assert CMCHeader.length == 32
        assert CMCHeader.State.LOG.value == "LOG    "
        assert CMCHeader.State.RESULT.value == "RESULT "
        assert CMCHeader.State.END_OF_REPLY.value == "ENDREPL"
        assert CMCHeader.default_protocol_name() == "fetch"


class TestCMCMessage:
    @pytest.mark.parametrize("count", list(range(10)))
    def test_result_answer(self, count):
        fetcher_payload = AgentResultMessage(AgentRawData(69 * b"\xff"))
        fetcher_stats = ResultStats(Snapshot.null())
        fetcher_message = FetcherMessage(
            FetcherHeader(
                FetcherType.TCP,
                PayloadType.AGENT,
                status=42,
                payload_length=len(fetcher_payload),
                stats_length=len(fetcher_stats),
            ),
            fetcher_payload,
            fetcher_stats,
        )
        fetcher_messages = list(repeat(fetcher_message, count))
        timeout = 7

        message = CMCMessage.result_answer(fetcher_messages, timeout, Snapshot.null())
        assert isinstance(repr(message), str)
        assert CMCMessage.from_bytes(bytes(message)) == message
        assert message.header.name == "fetch"
        assert message.header.state == CMCHeader.State.RESULT
        assert message.header.log_level.strip() == ""
        assert message.header.payload_length == len(message) - len(message.header)
        assert message.header.payload_length == len(message.payload)

    def test_log_answer(self):
        log_message = "the log message"
        level = logging.WARN

        message = CMCMessage.log_answer(log_message, level)
        assert isinstance(repr(message), str)
        assert CMCMessage.from_bytes(bytes(message)) == message
        assert message.header.name == "fetch"
        assert message.header.state == CMCHeader.State.LOG
        assert message.header.log_level.strip() == "warning"
        assert message.header.payload_length == len(message) - len(message.header)
        assert message.header.payload_length == len(log_message)

    def test_end_of_reply(self):
        message = CMCMessage.end_of_reply()
        assert isinstance(repr(message), str)
        assert CMCMessage.from_bytes(bytes(message)) is message


class TestCMCResultsStats:
    @pytest.fixture
    def stats(self):
        return FetcherResultsStats(7, Snapshot.null())

    def test_from_bytes(self, stats):
        assert isinstance(repr(stats), str)
        assert FetcherResultsStats.from_bytes(bytes(stats))


class TestCMCResults:
    @pytest.fixture
    def messages(self):
        msg = []
        for payload, stats in (
            (AgentResultMessage(AgentRawData(42 * b"\0")), ResultStats(Snapshot.null())),
            (AgentResultMessage(AgentRawData(12 * b"\0")), ResultStats(Snapshot.null())),
        ):
            msg.append(
                FetcherMessage(
                    FetcherHeader(
                        FetcherType.TCP,
                        PayloadType.AGENT,
                        status=69,
                        payload_length=len(payload),
                        stats_length=len(stats),
                    ),
                    payload,
                    stats,
                )
            )
        return msg

    @pytest.fixture
    def payload(self, messages):
        return CMCResults(messages, FetcherResultsStats(7, Snapshot.null()))

    def test_from_bytes(self, payload):
        assert CMCResults.from_bytes(bytes(payload)) == payload


class TestCMCLogging:
    @pytest.fixture
    def payload(self):
        return CMCLogging("This is very interesting!")

    def test_from_bytes(self, payload):
        assert CMCLogging.from_bytes(bytes(payload)) == payload


class TestCMCEndOfReply:
    @pytest.fixture
    def eor(self):
        return CMCMessage.end_of_reply()

    def test_from_bytes(self, eor):
        assert CMCMessage.from_bytes(bytes(eor)) is eor


class TestAgentResultMessage:
    @pytest.fixture
    def agent_payload(self):
        return AgentResultMessage(AgentRawData(b"<<<hello>>>\nworld"))

    def test_from_bytes_success(self, agent_payload):
        assert AgentResultMessage.from_bytes(bytes(agent_payload)) == agent_payload


class TestSNMPResultMessage:
    @pytest.fixture
    def snmp_payload(self):
        table: Sequence[SNMPTable] = []
        return SNMPResultMessage({SectionName("name"): table})

    def test_from_bytes_success(self, snmp_payload):
        assert SNMPResultMessage.from_bytes(bytes(snmp_payload)) == snmp_payload


class TestErrorResultMessage:
    @pytest.fixture(
        params=[
            # Our special exceptions.
            MKException,
            MKGeneralException,
            MKTerminate,
            MKBailOut,
            MKTimeout,
            MKSNMPError,
            MKIPAddressLookupError,
            # Python exceptions
            KeyError,
            LookupError,
            SyntaxError,
            ValueError,
            # Nested Python exceptions
            socket.herror,
            socket.timeout,
            # Third-party exceptions
            pyghmi.exceptions.IpmiException,
        ]
    )
    def exception(self, request):
        try:
            raise request.param("some helpful message")
        except Exception as exc:
            return exc

    @pytest.fixture
    def error(self, exception):
        return ErrorResultMessage(exception)

    def test_exception_serialization(self, exception, error):
        assert exception.__traceback__
        assert error.result().error is exception

        other = ErrorResultMessage.from_bytes(bytes(error))
        other_exc = other.result().error

        assert type(other_exc) is type(exception)
        assert other_exc.args == exception.args
        assert not other_exc.__traceback__

    def test_from_bytes_success(self, error):
        other = ErrorResultMessage.from_bytes(bytes(error))
        assert other is not error
        assert other == error
        assert type(other.result().error) == type(error.result().error)  # pylint: disable=C0123
        assert other.result().error.args == error.result().error.args

    def test_from_bytes_failure(self):
        with pytest.raises(ValueError):
            ErrorResultMessage.from_bytes(b"random bytes")

    def test_hash(self, error):
        assert hash(error) == hash(bytes(error))

    def test_len(self, error):
        assert len(error) == len(bytes(error))


class TestFetcherHeader:
    @pytest.fixture
    def header(self):
        return FetcherHeader(
            FetcherType.TCP,
            PayloadType.AGENT,
            status=42,
            payload_length=69,
            stats_length=1337,
        )

    def test_from_bytes_success(self, header):
        assert FetcherHeader.from_bytes(bytes(header) + 42 * b"*") == header

    def test_from_bytes_failure(self):
        with pytest.raises(ValueError):
            FetcherHeader.from_bytes(b"random bytes")

    def test_repr(self, header):
        assert isinstance(repr(header), str)

    def test_hash(self, header):
        assert hash(header) == hash(bytes(header))

    def test_len(self, header):
        assert len(header) == len(bytes(header))
        assert len(header) == FetcherHeader.length


class TestFetcherHeaderEq:
    @pytest.fixture
    def fetcher_type(self):
        return FetcherType.NONE

    @pytest.fixture
    def payload_type(self):
        return PayloadType.AGENT

    @pytest.fixture
    def status(self):
        return 42

    @pytest.fixture
    def payload_length(self):
        return 69

    @pytest.fixture
    def stats_length(self):
        return len(ResultStats(Snapshot.null()))

    @pytest.fixture
    def header(self, fetcher_type, payload_type, status, payload_length, stats_length):
        return FetcherHeader(
            fetcher_type,
            payload_type,
            status=status,
            payload_length=payload_length,
            stats_length=stats_length,
        )

    def test_eq(self, header, fetcher_type, payload_type, status, payload_length, stats_length):
        assert header == bytes(header)
        assert bytes(header) == header
        assert bytes(header) == bytes(header)
        assert header == FetcherHeader(
            fetcher_type,
            payload_type,
            status=status,
            payload_length=payload_length,
            stats_length=stats_length,
        )

    def test_neq_other_payload_type(self, header):
        other = FetcherType.TCP
        assert other != header.payload_type

        assert header != FetcherHeader(
            other,
            payload_type=header.payload_type,
            status=header.status,
            payload_length=header.payload_length,
            stats_length=header.stats_length,
        )

    def test_neq_other_result_type(self, header):
        other = PayloadType.ERROR
        assert other != header.payload_type

        assert header != FetcherHeader(
            header.fetcher_type,
            other,
            status=header.status,
            payload_length=header.payload_length,
            stats_length=header.stats_length,
        )

    def test_neq_other_status(self, header, status):
        other = status + 1
        assert other != header.status

        assert header != FetcherHeader(
            header.fetcher_type,
            header.payload_type,
            status=other,
            payload_length=header.payload_length,
            stats_length=header.stats_length,
        )

    def test_neq_other_payload_length(self, header, payload_length):
        other = payload_length + 1
        assert other != header.payload_length

        assert header != FetcherHeader(
            header.fetcher_type,
            header.payload_type,
            status=header.status,
            payload_length=other,
            stats_length=header.stats_length,
        )

    def test_add(self, header, payload_length):
        payload = payload_length * b"\0"

        message = header + payload
        assert isinstance(message, bytes)
        assert len(message) == len(header) + len(payload)
        assert FetcherHeader.from_bytes(message) == header
        assert FetcherHeader.from_bytes(message[: len(header)]) == header
        assert message[len(header) :] == payload


class TestResultStats:
    @pytest.fixture
    def l3stats(self):
        return ResultStats(Snapshot.null())

    def test_encode_decode(self, l3stats):
        assert ResultStats.from_bytes(bytes(l3stats)) == l3stats


class TestFetcherMessage:
    @pytest.fixture
    def duration(self):
        return Snapshot.null()

    @pytest.fixture
    def stats(self, duration):
        return ResultStats(duration)

    @pytest.fixture
    def header(self, stats):
        return FetcherHeader(
            FetcherType.TCP,
            PayloadType.AGENT,
            status=42,
            payload_length=69,
            stats_length=len(stats),
        )

    @pytest.fixture
    def payload(self, header):
        return AgentResultMessage(b"\0" * (header.payload_length - AgentResultMessage.length))

    @pytest.fixture
    def message(self, header, payload, stats):
        return FetcherMessage(header, payload, stats)

    @pytest.fixture
    def snmp_raw_data(self):
        table: Sequence[SNMPTable] = [[[6500337, 11822045]]]
        return {SectionName("snmp_uptime"): table}

    @pytest.fixture
    def agent_raw_data(self):
        return AgentRawData(b"<<<check_mk>>>")

    def test_accessors(self, message, header, payload):
        assert message.header == header

    def test_from_bytes_success(self, message):
        assert FetcherMessage.from_bytes(bytes(message) + 42 * b"*") == message

    def test_from_bytes_failure(self):
        with pytest.raises(ValueError):
            FetcherMessage.from_bytes(b"random bytes")

    def test_len(self, message, header, payload, stats):
        assert len(message) == len(header) + len(payload) + len(stats)

    @pytest.mark.parametrize("fetcher_type", [FetcherType.TCP])
    def test_from_raw_data_standard(self, agent_raw_data, duration, fetcher_type):
        raw_data: result.Result[AgentRawData, Exception] = result.OK(agent_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, duration, fetcher_type)
        assert message.header.fetcher_type is fetcher_type
        assert message.header.payload_type is PayloadType.AGENT
        assert message.raw_data == raw_data

    def test_from_raw_data_snmp(self, snmp_raw_data, duration):
        raw_data: result.Result[SNMPRawData, Exception] = result.OK(snmp_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, duration, FetcherType.SNMP)
        assert message.header.fetcher_type is FetcherType.SNMP
        assert message.header.payload_type is PayloadType.SNMP
        assert message.raw_data == raw_data

    def test_from_raw_data_exception(self, duration):
        error: result.Result[AgentRawData, Exception] = result.Error(ValueError("zomg!"))
        message = FetcherMessage.from_raw_data(error, duration, FetcherType.TCP)
        assert message.header.fetcher_type is FetcherType.TCP
        assert message.header.payload_type is PayloadType.ERROR
        # Comparison of exception is "interesting" in Python so we check the type and args.
        assert type(message.raw_data.error) is type(error.error)
        assert message.raw_data.error.args == error.error.args

    @pytest.mark.parametrize("fetcher_type", [FetcherType.TCP])
    def test_raw_data_tcp_standard(self, agent_raw_data, duration, fetcher_type):
        raw_data: result.Result[AgentRawData, Exception] = result.OK(agent_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, duration, fetcher_type)
        assert message.raw_data == raw_data

    def test_raw_data_snmp(self, snmp_raw_data, duration):
        raw_data: result.Result[SNMPRawData, Exception] = result.OK(snmp_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, duration, FetcherType.SNMP)
        assert message.raw_data == raw_data

    def test_raw_data_exception(self, duration):
        raw_data: result.Result[AgentRawData, Exception] = result.Error(Exception("zomg!"))
        message = FetcherMessage.from_raw_data(raw_data, duration, FetcherType.TCP)
        assert isinstance(message.raw_data.error, Exception)
        assert str(message.raw_data.error) == "zomg!"
