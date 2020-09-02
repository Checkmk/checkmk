#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]

from cmk.fetchers import FetcherType
from cmk.fetchers.controller import (
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
        assert make_success_answer(
            data=b"payload") == b"fetch:SUCCESS :               :7       :payload"

    def test_controller_failure(self):
        assert make_failure_answer(
            data=b"payload",
            severity="0123456789ABCDEF") == b"fetch:FAILURE :0123456789ABCDE:7       :payload"

    def test_controller_waiting(self):
        assert make_waiting_answer() == b"fetch:WAITING :               :0       :"

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
        header = Header(name="name", state=state, hint="crit", payload_length=41)
        assert str(header) == "name :SUCCESS :crit           :41      :"

    @pytest.mark.parametrize("state", [Header.State.FAILURE, "FAILURE"])
    def test_failure_header(self, state):
        header = Header(name="fetch", state=state, hint="crit", payload_length=42)
        assert str(header) == "fetch:FAILURE :crit           :42      :"

    def test_from_network(self):
        header = Header(name="fetch", state="SUCCESS", hint="crit", payload_length=42)
        assert Header.from_network(bytes(header) + b"*" * 42) == header

    def test_eq(self):
        header = Header(
            name="name",
            state=Header.State.SUCCESS,
            hint="crit",
            payload_length=42,
        )
        assert header == str(header)
        assert str(header) == header

    def test_neq(self):
        name = "name"
        state = "state"
        hint = "hint"
        payload_length = 42

        header = Header(name=name, state=state, hint=hint, payload_length=payload_length)

        assert name != "other"
        assert header != Header(
            name="other",
            state=state,
            hint=hint,
            payload_length=payload_length,
        )

        assert state != "other"
        assert header != Header(
            name=name,
            state="other",
            hint=hint,
            payload_length=payload_length,
        )

        assert hint != "other"
        assert header != Header(
            name=name,
            state=state,
            hint="other",
            payload_length=payload_length,
        )

        assert payload_length != 69
        assert header != Header(
            name=name,
            state=state,
            hint=hint,
            payload_length=69,
        )

    def test_repr(self):
        header = Header(name="name", state="SUCCESS", hint="crit", payload_length=42)
        assert isinstance(repr(header), str)

    def test_hash(self):
        header = Header(name="name", state="SUCCESS", hint="crit", payload_length=42)
        assert hash(header) == hash(str(header))

    def test_len(self):
        header = Header(name="name", state="SUCCESS", hint="crit", payload_length=42)
        assert len(header) == len(str(header))

    def test_critical_constants(self):
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert Header.length == 40
        assert Header.default_protocol_name() == "fetch"
