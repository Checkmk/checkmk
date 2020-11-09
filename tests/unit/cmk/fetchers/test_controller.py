#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket

import pyghmi.exceptions  # type: ignore[import]
import pytest  # type: ignore[import]

import cmk.utils.log as log
from cmk.utils.cpu_tracking import CPUTracker
from cmk.utils.exceptions import (
    MKBailOut,
    MKException,
    MKGeneralException,
    MKIPAddressLookupError,
    MKSNMPError,
    MKTerminate,
    MKTimeout,
)
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.type_defs import (
    AgentRawData,
    ConfigSerial,
    result,
    SectionName,
)

from cmk.snmplib.type_defs import SNMPRawData, SNMPTable

from cmk.fetchers import FetcherType
from cmk.fetchers.controller import (
    AgentPayload,
    build_json_file_path,
    build_json_global_config_file_path,
    cmc_log_level_from_python,
    CMCHeader,
    CmcLogLevel,
    ErrorPayload,
    FetcherHeader,
    FetcherMessage,
    L3Stats,
    make_log_answer,
    make_result_answer,
    make_end_of_reply_answer,
    PayloadType,
    run_fetcher,
    SNMPPayload,
    write_bytes,
)
from cmk.fetchers.type_defs import Mode


@pytest.mark.parametrize("status,log_level", [
    (logging.CRITICAL, CmcLogLevel.CRITICAL),
    (logging.ERROR, CmcLogLevel.ERROR),
    (logging.WARNING, CmcLogLevel.WARNING),
    (logging.INFO, CmcLogLevel.INFO),
    (log.VERBOSE, CmcLogLevel.INFO),
    (logging.DEBUG, CmcLogLevel.DEBUG),
    (5, CmcLogLevel.WARNING),
])
def test_status_to_log_level(status, log_level):
    assert log_level == cmc_log_level_from_python(status)


class TestControllerApi:
    def test_controller_result(self):
        payload = AgentPayload(69 * b"\0")
        stats = L3Stats(CPUTracker())
        header = FetcherHeader(
            FetcherType.TCP,
            PayloadType.AGENT,
            status=42,
            payload_length=len(payload),
            stats_length=len(stats),
        )
        message = FetcherMessage(header, payload, stats)
        assert make_result_answer(message) == (b"fetch:RESULT :        :240     :" + header +
                                               payload + stats)

    def test_controller_log(self):
        assert make_log_answer(
            "payload", log_level=CmcLogLevel.WARNING) == b"fetch:LOG    :warning :7       :payload"

    def test_controller_end_of_reply(self):
        assert make_end_of_reply_answer() == b"fetch:ENDREPL:        :0       :"

    def test_build_json_file_path(self):
        assert build_json_file_path(serial=ConfigSerial("_serial_"),
                                    host_name="buzz") == (core_helper_config_dir / "_serial_" /
                                                          "fetchers" / "hosts" / "buzz.json")

    def test_build_json_global_config_file_path(self):
        assert build_json_global_config_file_path(serial=ConfigSerial(
            "_serial_")) == core_helper_config_dir / "_serial_" / "fetchers" / "global_config.json"

    def test_run_fetcher_with_failure(self):
        message = run_fetcher(
            {
                "fetcher_type": "SNMP",
                "trash": 1
            },
            Mode.CHECKING,
        )
        assert message.header.fetcher_type is FetcherType.SNMP
        assert message.header.status == 50
        assert message.header.payload_length == (len(message) - len(message.header) -
                                                 message.header.stats_length)
        assert type(message.raw_data.error) is KeyError  # pylint: disable=C0123
        assert str(message.raw_data.error) == repr("fetcher_params")

    def test_run_fetcher_with_exception(self):
        with pytest.raises(RuntimeError):
            run_fetcher({"trash": 1}, Mode.CHECKING)

    def test_write_bytes(self, capfdbinary):
        write_bytes(b"123")
        captured = capfdbinary.readouterr()
        assert captured.out == b"123"
        assert captured.err == b""


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
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert CMCHeader.length == 32
        assert CMCHeader.State.LOG.value == "LOG    "
        assert CMCHeader.State.RESULT.value == "RESULT "
        assert CMCHeader.State.END_OF_REPLY.value == "ENDREPL"
        assert CMCHeader.default_protocol_name() == "fetch"


class TestAgentPayload:
    @pytest.fixture
    def payload(self):
        return AgentPayload(b"<<<hello>>>\nworld")

    def test_from_bytes_success(self, payload):
        assert AgentPayload.from_bytes(bytes(payload)) == payload


class TestSNMPPayload:
    @pytest.fixture
    def payload(self):
        table: SNMPTable = []
        return SNMPPayload({SectionName("name"): table})

    def test_from_bytes_success(self, payload):
        assert SNMPPayload.from_bytes(bytes(payload)) == payload


class TestErrorPayload:
    @pytest.fixture(params=[
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
    ])
    def error(self, request):
        return ErrorPayload(request.param("a very helpful message"))

    def test_from_bytes_success(self, error):
        other = ErrorPayload.from_bytes(bytes(error))
        assert other is not error
        assert other == error
        assert type(other.result().error) == type(error.result().error)  # pylint: disable=C0123
        assert other.result().error.args == error.result().error.args

    def test_from_bytes_failure(self):
        with pytest.raises(ValueError):
            ErrorPayload.from_bytes(b"random bytes")

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
        return len(L3Stats(CPUTracker()))

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
        assert FetcherHeader.from_bytes(message[:len(header)]) == header
        assert message[len(header):] == payload


class TestL3Stats:
    @pytest.fixture
    def tracker(self):
        return CPUTracker()

    @pytest.fixture
    def l3stats(self, tracker):
        return L3Stats(tracker)

    def test_encode_decode(self, l3stats):
        assert L3Stats.from_bytes(bytes(l3stats)) == l3stats


class TestFetcherMessage:
    @pytest.fixture
    def stats(self):
        return L3Stats(CPUTracker())

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
        return AgentPayload(b"\0" * (header.payload_length - AgentPayload.length))

    @pytest.fixture
    def message(self, header, payload, stats):
        return FetcherMessage(header, payload, stats)

    @pytest.fixture
    def snmp_raw_data(self):
        table: SNMPTable = [[[6500337, 11822045]]]
        raw_data: SNMPRawData = {SectionName('snmp_uptime'): table}
        return raw_data

    @pytest.fixture
    def agent_raw_data(self):
        return b"<<<check_mk>>>"

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
    def test_from_raw_data_standard(self, agent_raw_data, stats, fetcher_type):
        raw_data: result.Result[AgentRawData, Exception] = result.OK(agent_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, stats, fetcher_type)
        assert message.header.fetcher_type is fetcher_type
        assert message.header.payload_type is PayloadType.AGENT
        assert message.raw_data == raw_data

    def test_from_raw_data_snmp(self, snmp_raw_data, stats):
        raw_data: result.Result[SNMPRawData, Exception] = result.OK(snmp_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, stats, FetcherType.SNMP)
        assert message.header.fetcher_type is FetcherType.SNMP
        assert message.header.payload_type is PayloadType.SNMP
        assert message.raw_data == raw_data

    def test_from_raw_data_exception(self, stats):
        error: result.Result[AgentRawData, Exception] = result.Error(ValueError("zomg!"))
        message = FetcherMessage.from_raw_data(error, stats, FetcherType.TCP)
        assert message.header.fetcher_type is FetcherType.TCP
        assert message.header.payload_type is PayloadType.ERROR
        # Comparison of exception is "interesting" in Python so we check the type and args.
        assert type(message.raw_data.error) is type(error.error)
        assert message.raw_data.error.args == error.error.args

    @pytest.mark.parametrize("fetcher_type", [FetcherType.TCP])
    def test_raw_data_tcp_standard(self, agent_raw_data, stats, fetcher_type):
        raw_data: result.Result[AgentRawData, Exception] = result.OK(agent_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, stats, fetcher_type)
        assert message.raw_data == raw_data

    def test_raw_data_snmp(self, snmp_raw_data, stats):
        raw_data: result.Result[SNMPRawData, Exception] = result.OK(snmp_raw_data)
        message = FetcherMessage.from_raw_data(raw_data, stats, FetcherType.SNMP)
        assert message.raw_data == raw_data

    def test_raw_data_exception(self, stats):
        raw_data: result.Result[AgentRawData, Exception] = result.Error(Exception("zomg!"))
        message = FetcherMessage.from_raw_data(raw_data, stats, FetcherType.TCP)
        assert isinstance(message.raw_data.error, Exception)
        assert str(message.raw_data.error) == "zomg!"
