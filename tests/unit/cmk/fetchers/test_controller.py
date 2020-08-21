#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import socket
from pathlib import Path

import importlib

from typing import List

import pytest  # type: ignore[import]

import cmk.fetchers.controller

from cmk.fetchers.controller import (
    Header,
    make_failure_answer,
    make_success_answer,
    make_waiting_answer,
    build_json_file_path,
    build_json_global_config_file_path,
    run_fetchers,
    load_global_config,
)

from cmk.base.cee.fetcher_config import FetcherConfig
from cmk.fetchers.tcp import TCPFetcher

from cmk.utils.paths import core_fetcher_config_dir
import cmk.utils.paths
import cmk.utils.log

import testlib.base as base


class TestControllerApi:
    def test_controller_success(self):
        assert make_success_answer(data="payload") == "fetch:SUCCESS:        :7       :payload"

    def test_controller_failure(self):
        assert make_failure_answer(
            data="payload", severity="crit12345678") == "fetch:FAILURE:crit1234:7       :payload"

    def test_controller_waiting(self):
        assert make_waiting_answer() == "fetch:WAITING:        :0       :"

    def test_build_json_file_path(self):
        assert build_json_file_path(
            serial="_serial_",
            host_name="buzz") == Path(core_fetcher_config_dir) / "_serial_" / "buzz.json"

    def test_build_json_global_config_file_path(self):
        assert build_json_global_config_file_path(
            serial="_serial_") == Path(core_fetcher_config_dir) / "_serial_" / "global_config.json"

    @pytest.fixture
    def scenario(self, monkeypatch, tmp_path):
        def write_to_stdout(data: str) -> None:
            sys.stdout.write(data)

        ts = base.Scenario()
        ts.add_host("heute")
        ts.add_host("rrd_host")
        ts.set_option("ipaddresses", {"heute": "127.0.0.1", "rrd_host": "127.0.0.2"})
        ts.apply(monkeypatch)

        def _dummy_connect(s):
            s._socket = socket.socket(s._family, socket.SOCK_STREAM)
            return s

        # Prevent agent communication
        monkeypatch.setattr(TCPFetcher, "__enter__", _dummy_connect)
        monkeypatch.setattr(TCPFetcher, "_raw_data", lambda self: b"<<<check_mk>>>abc")

        monkeypatch.setattr("cmk.utils.paths.core_fetcher_config_dir", tmp_path)
        importlib.reload(cmk.fetchers.controller)

        # write_out cannot be used with capsys - monkeypatching this!
        # More complicated method of testing may be written in the future
        monkeypatch.setattr(cmk.fetchers.controller, "write_data", write_to_stdout)

    @pytest.fixture
    def scenario_short(self, monkeypatch, tmp_path):
        monkeypatch.setattr("cmk.utils.paths.core_fetcher_config_dir", tmp_path)
        importlib.reload(cmk.fetchers.controller)

        fetcher_config = FetcherConfig()
        fetcher_config.write_global()

    @staticmethod
    @pytest.fixture
    def expected_error() -> str:
        return 'TCP: Not connected'

    @staticmethod
    @pytest.fixture
    def write_config() -> int:
        ff = FetcherConfig()
        ff.write("heute")
        return ff.serial

    @staticmethod
    @pytest.fixture
    def expected_blob() -> str:
        def make_blob(fetcher: str, status: int, payload: str) -> str:
            return '{"fetcher_type": "%s", "status": %d, "payload": "%s"}' % (fetcher, status,
                                                                              payload)

        return '[%s, %s]' % (make_blob("TCP", 0, "<<<check_mk>>>abc"), make_blob(
            "PIGGYBACK", 0, ""))

    @pytest.mark.parametrize("the_host", ["heute", "rrd_host"])
    @pytest.mark.usefixtures("scenario")
    def test_run_fetchers(self, the_host, capsys, expected_error, expected_blob):
        fetcher_config = FetcherConfig()
        fetcher_config.write(hostname=the_host)
        run_fetchers(serial=str(fetcher_config.serial), host_name=the_host, timeout=35)
        captured = capsys.readouterr()
        assert captured.out == make_success_answer(expected_blob) + make_waiting_answer()

    @pytest.mark.usefixtures("scenario")
    def test_run_fetchers_bad_file(self, capsys, write_config):
        run_fetchers(serial=str(write_config), host_name="zzz", timeout=35)
        captured = capsys.readouterr()
        text = f"fetcher file for host 'zzz' and {write_config} is absent"
        assert captured.out == make_success_answer(text) + make_failure_answer(
            text, severity="warning") + make_waiting_answer()

    @pytest.mark.usefixtures("scenario")
    def test_run_fetchers_bad_serial(self, capsys, write_config):
        run_fetchers(serial=str(write_config + 1), host_name="heute", timeout=35)
        captured = capsys.readouterr()
        text = f"fetcher file for host 'heute' and {write_config + 1} is absent"
        assert captured.out == make_success_answer(text) + make_failure_answer(
            text, severity="warning") + make_waiting_answer()

    @pytest.mark.usefixtures("scenario_short")
    def test_log_level(self, capsys, monkeypatch):
        result: List[int] = []

        def set_level(level: int):
            result.append(level)

        monkeypatch.setattr(cmk.utils.log.logger, "setLevel", set_level)

        load_global_config(13)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert result == [5]


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
        assert Header.from_network(str(header) + 42 * "*") == header

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
