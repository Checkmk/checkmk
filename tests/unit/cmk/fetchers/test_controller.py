#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest  # type: ignore[import]

import cmk.utils.log as log
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.type_defs import ConfigSerial

from cmk.fetchers import FetcherType
from cmk.fetchers.controller import (
    build_json_file_path,
    build_json_global_config_file_path,
    cmc_log_level_from_python,
    CmcLogLevel,
    FetcherHeader,
    PayloadType,
    Header,
    make_logging_answer,
    make_payload_answer,
    make_waiting_answer,
    run_fetcher,
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
    def test_controller_success(self):
        assert make_payload_answer(data=b"payload") == b"fetch:SUCCESS:        :7       :payload"

    def test_controller_failure(self):
        assert make_logging_answer(
            "payload", log_level=CmcLogLevel.WARNING) == b"fetch:FAILURE:warning :7       :payload"

    def test_controller_waiting(self):
        assert make_waiting_answer() == b"fetch:WAITING:        :0       :"

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
            13,
        )
        header = FetcherHeader.from_network(message)
        payload = message[len(header):]
        assert header.fetcher_type is FetcherType.SNMP
        assert header.status == 50
        assert header.payload_length == len(payload)
        assert payload == b"KeyError('fetcher_params')"

    def test_run_fetcher_with_exception(self):
        with pytest.raises(RuntimeError):
            run_fetcher({"trash": 1}, Mode.CHECKING, 13)

    def test_write_bytes(self, capfdbinary):
        write_bytes(b"123")
        captured = capfdbinary.readouterr()
        assert captured.out == b"123"
        assert captured.err == b""


class TestHeader:
    @pytest.mark.parametrize("state", [Header.State.SUCCESS, "SUCCESS"])
    def test_success_header(self, state):
        header = Header("name", state, "crit", 41)
        assert bytes(header) == b"name :SUCCESS:crit    :41      :"

    @pytest.mark.parametrize("state", [Header.State.FAILURE, "FAILURE"])
    def test_failure_header(self, state):
        header = Header("fetch", state, "crit", 42)
        assert bytes(header) == b"fetch:FAILURE:crit    :42      :"

    def test_from_network(self):
        header = Header("fetch", "SUCCESS", "crit", 42)
        assert Header.from_network(bytes(header) + 42 * b"*") == header

    def test_clone(self):
        header = Header("name", Header.State.SUCCESS, "crit", 42)
        other = header.clone()
        assert other is not header
        assert other == header

    def test_eq(self):
        header = Header("name", Header.State.SUCCESS, "crit", 42)
        assert header == bytes(header)
        assert bytes(header) == header

    def test_neq(self):
        header = Header("name", Header.State.SUCCESS, "crit", 42)

        other_name = header.clone()
        other_name.name = "toto"
        assert header != other_name

        other_state = header.clone()
        other_state.state = Header.State.FAILURE
        assert header != other_state

        other_crit = header.clone()
        other_crit.severity = "tnih"
        assert header != other_crit

        other_len = header.clone()
        other_len.payload_length = 69
        assert header != other_len

    def test_repr(self):
        header = Header("name", "SUCCESS", "crit", 42)
        assert isinstance(repr(header), str)

    def test_hash(self):
        header = Header("name", "SUCCESS", "crit", 42)
        assert hash(header) == hash(bytes(header))

    def test_len(self):
        header = Header("name", "SUCCESS", "crit", 42)
        assert len(header) == len(bytes(header))

    def test_critical_constants(self):
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert Header.length == 32
        assert Header.State.FAILURE == "FAILURE"
        assert Header.State.SUCCESS == "SUCCESS"
        assert Header.State.WAITING == "WAITING"
        assert Header.default_protocol_name() == "fetch"


class TestFetcherHeader:
    @pytest.fixture
    def header(self):
        return FetcherHeader(
            FetcherType.TCP,
            PayloadType.AGENT,
            status=42,
            payload_length=69,
        )

    def test_from_network(self, header):
        assert FetcherHeader.from_network(bytes(header) + 42 * b"*") == header

    def test_from_network_failure(self):
        with pytest.raises(ValueError):
            FetcherHeader.from_network(b"random bytes")

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
    def header(self, fetcher_type, payload_type, status, payload_length):
        return FetcherHeader(
            fetcher_type,
            payload_type,
            status=status,
            payload_length=payload_length,
        )

    def test_eq(self, header, fetcher_type, payload_type, status, payload_length):
        assert header == bytes(header)
        assert bytes(header) == header
        assert bytes(header) == bytes(header)
        assert header == FetcherHeader(
            fetcher_type,
            payload_type,
            status=status,
            payload_length=payload_length,
        )

    def test_neq_other_payload_type(self, header):
        other = FetcherType.TCP
        assert other != header.payload_type

        assert header != FetcherHeader(
            other,
            payload_type=header.payload_type,
            status=header.status,
            payload_length=header.payload_length,
        )

    def test_neq_other_result_type(self, header):
        other = PayloadType.ERROR
        assert other != header.payload_type

        assert header != FetcherHeader(
            header.fetcher_type,
            other,
            status=header.status,
            payload_length=header.payload_length,
        )

    def test_neq_other_status(self, header, status):
        other = status + 1
        assert other != header.status

        assert header != FetcherHeader(
            header.fetcher_type,
            header.payload_type,
            status=other,
            payload_length=header.payload_length,
        )

    def test_neq_other_payload_length(self, header, payload_length):
        other = payload_length + 1
        assert other != header.payload_length

        assert header != FetcherHeader(
            header.fetcher_type,
            header.payload_type,
            status=header.status,
            payload_length=other,
        )

    def test_add(self, header, payload_length):
        payload = payload_length * b"\0"

        message = header + payload
        assert isinstance(message, bytes)
        assert len(message) == len(header) + len(payload)
        assert FetcherHeader.from_network(message) == header
        assert FetcherHeader.from_network(message[:len(header)]) == header
        assert message[len(header):] == payload
