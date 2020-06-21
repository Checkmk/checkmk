#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]

from cmk.fetchers.controller import (Header, make_failure_answer, make_success_answer,
                                     build_json_file_path)
from cmk.utils.paths import core_fetcher_config_dir


def test_controller_success():
    assert make_success_answer(data="payload") == "fetch:SUCCESS:        :7       :payload"


def test_controller_failure():
    assert make_failure_answer(data="payload",
                               hint="hint12345678") == "fetch:FAILURE:hint1234:7       :payload"


def test_build_json_file_path():
    assert build_json_file_path(
        serial="_serial_", host="buzz") == Path(core_fetcher_config_dir) / "_serial_" / "buzz.mk"


class TestHeader:
    @pytest.mark.parametrize("state", [Header.State.SUCCESS, "SUCCESS"])
    def test_success_header(self, state):
        header = Header("name", state, "hint", 41)
        assert str(header) == "name :SUCCESS:hint    :41      :"

    @pytest.mark.parametrize("state", [Header.State.FAILURE, "FAILURE"])
    def test_failure_header(self, state):
        header = Header("fetch", state, "hint", 42)
        assert str(header) == "fetch:FAILURE:hint    :42      :"

    def test_from_network(self):
        header = Header("fetch", "SUCCESS", "hint", 42)
        assert Header.from_network(str(header) + 42 * "*") == header

    def test_clone(self):
        header = Header("name", Header.State.SUCCESS, "hint", 42)
        other = header.clone()
        assert other is not header
        assert other == header

    def test_eq(self):
        header = Header("name", Header.State.SUCCESS, "hint", 42)
        assert header == str(header)
        assert str(header) == header

    def test_neq(self):
        header = Header("name", Header.State.SUCCESS, "hint", 42)

        other_name = header.clone()
        other_name.name = "toto"
        assert header != other_name

        other_state = header.clone()
        other_state.state = Header.State.FAILURE
        assert header != other_state

        other_hint = header.clone()
        other_hint.hint = "tnih"
        assert header != other_hint

        other_len = header.clone()
        other_len.payload_length = 69
        assert header != other_len

    def test_repr(self):
        header = Header("name", "SUCCESS", "hint", 42)
        assert isinstance(repr(header), str)

    def test_hash(self):
        header = Header("name", "SUCCESS", "hint", 42)
        assert hash(header) == hash(str(header))

    def test_len(self):
        header = Header("name", "SUCCESS", "hint", 42)
        assert len(header) == len(str(header))

    def test_critical_constants(self):
        """ ATTENTION: Changing of those constants may require changing of C++ code"""
        assert Header.length == 32
        assert Header.State.FAILURE == "FAILURE"
        assert Header.State.SUCCESS == "SUCCESS"
        assert Header.default_protocol_name() == "fetch"
