#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]

from cmk.fetchers import FetcherType
from cmk.fetchers.controller import (
    FetcherHeader,
    Header,
    make_failure_answer,
    make_success_answer,
    make_waiting_answer,
    build_json_file_path,
    build_json_global_config_file_path,
    status_to_microcore_severity,
)

from cmk.utils.paths import core_fetcher_config_dir


@pytest.mark.parametrize("status,severity", [
    (50, "critical"),
    (40, "error"),
    (30, "warning"),
    (20, "info"),
    (15, "info"),
    (10, "debug"),
    (5, "warning"),
])
def test_status_to_severity(status, severity):
    assert severity == status_to_microcore_severity(status)


class TestControllerApi:
    def test_controller_success(self):
        assert make_success_answer(data=b"payload") == b"fetch:SUCCESS:        :7       :payload"

    def test_controller_failure(self):
        assert make_failure_answer(
            data=b"payload", severity="crit12345678") == b"fetch:FAILURE:crit1234:7       :payload"

    def test_controller_waiting(self):
        assert make_waiting_answer() == b"fetch:WAITING:        :0       :"

    def test_build_json_file_path(self):
        assert build_json_file_path(
            serial="_serial_",
            host_name="buzz") == Path(core_fetcher_config_dir) / "_serial_" / "buzz.json"

    def test_build_json_global_config_file_path(self):
        assert build_json_global_config_file_path(
            serial="_serial_") == Path(core_fetcher_config_dir) / "_serial_" / "global_config.json"


class TestHeader:
    @pytest.mark.parametrize("state", [Header.State.SUCCESS, "SUCCESS"])
    def test_success_header(self, state):
        header = Header("name", state, "crit", 41)
        assert str(header) == "name :SUCCESS:crit    :41      :"

    @pytest.mark.parametrize("state", [Header.State.FAILURE, "FAILURE"])
    def test_failure_header(self, state):
        header = Header("fetch", state, "crit", 42)
        assert str(header) == "fetch:FAILURE:crit    :42      :"

    def test_from_network(self):
        header = Header("fetch", "SUCCESS", "crit", 42)
        assert Header.from_network(bytes(header) + b"*" * 42) == header

    def test_clone(self):
        header = Header("name", Header.State.SUCCESS, "crit", 42)
        other = header.clone()
        assert other is not header
        assert other == header

    def test_eq(self):
        header = Header("name", Header.State.SUCCESS, "crit", 42)
        assert header == str(header)
        assert str(header) == header

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
        assert hash(header) == hash(str(header))

    def test_len(self):
        header = Header("name", "SUCCESS", "crit", 42)
        assert len(header) == len(str(header))

    def test_critical_constants(self):
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert Header.length == 32
        assert Header.State.FAILURE == "FAILURE"
        assert Header.State.SUCCESS == "SUCCESS"
        assert Header.State.WAITING == "WAITING"
        assert Header.default_protocol_name() == "fetch"


class TestFetcherHeader:
    def test_str(self):
        f_header = FetcherHeader(FetcherType.TCP, status=1, payload_length=42)
        assert len(str(f_header)) == FetcherHeader.length
        assert str(f_header) == "TCP            :1      :42     :"

    def test_from_network(self):
        f_header = FetcherHeader(FetcherType.TCP, status=1, payload_length=42)
        assert FetcherHeader.from_network(bytes(f_header) + b"*" * 42) == f_header

    def test_clone(self):
        f_header = FetcherHeader(FetcherType.TCP, status=1, payload_length=42)
        other = f_header.clone()
        assert other is not f_header
        assert other == f_header

    def test_eq(self):
        f_header = FetcherHeader(FetcherType.TCP, status=1, payload_length=42)
        assert f_header == str(f_header)
        assert str(f_header) == f_header

    def test_neq(self):
        type_ = FetcherType.TCP
        status = 1
        payload_length = 42

        assert (FetcherHeader(
            type_,
            status=status,
            payload_length=payload_length,
        ) != FetcherHeader(
            FetcherType.SNMP,  # other type
            status=status,
            payload_length=payload_length,
        ))

        assert (FetcherHeader(
            type_,
            status=status,
            payload_length=payload_length,
        ) != FetcherHeader(
            type_,
            status=69,  # other status
            payload_length=payload_length,
        ))

        assert (FetcherHeader(
            type_,
            status=status,
            payload_length=payload_length,
        ) != FetcherHeader(
            type_,
            status=status,
            payload_length=69,  # other length
        ))

    def test_repr(self):
        f_header = FetcherHeader(FetcherType.TCP, status=0, payload_length=42)
        assert isinstance(repr(f_header), str)

    def test_hash(self):
        f_header = FetcherHeader(FetcherType.TCP, status=0, payload_length=42)
        assert hash(f_header) == hash(str(f_header))

    def test_len(self):
        f_header = FetcherHeader(FetcherType.TCP, status=0, payload_length=42)
        assert len(f_header) == len(str(f_header))

    def test_critical_constants(self):
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert FetcherHeader.length == 32
