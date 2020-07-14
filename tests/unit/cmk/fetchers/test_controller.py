#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
import socket

import importlib

import pytest  # type: ignore[import]

from cmk.fetchers.controller import (
    FetcherFactory,
    Header,
    make_failure_answer,
    make_success_answer,
    make_waiting_answer,
    build_json_file_path,
    run_fetchers,
)
from cmk.fetchers import (
    SNMPDataFetcher,
    TCPDataFetcher,
    ProgramDataFetcher,
)

from cmk.utils.paths import core_fetcher_config_dir
import cmk.utils.paths
import cmk.base.cee.core_cmc as core_cmc

import testlib.base as base


class TestControllerApi:
    def test_controller_success(self):
        assert make_success_answer(data="payload") == "fetch:SUCCESS:        :7       :payload"

    def test_controller_failure(self):
        assert make_failure_answer(data="payload",
                                   hint="hint12345678") == "fetch:FAILURE:hint1234:7       :payload"

    def test_controller_waiting(self):
        assert make_waiting_answer() == "fetch:WAITING:        :0       :"

    def test_build_json_file_path(self):
        assert build_json_file_path(
            serial="_serial_",
            host_name="buzz") == Path(core_fetcher_config_dir) / "_serial_" / "buzz.json"

    @pytest.fixture
    def scenario(self, monkeypatch, tmp_path):
        ts = base.Scenario()
        ts.add_host("heute")
        ts.add_host("rrd_host")
        ts.set_option("ipaddresses", {"heute": "127.0.0.1", "rrd_host": "127.0.0.2"})
        ts.apply(monkeypatch)
        monkeypatch.setattr("cmk.utils.paths.core_fetcher_config_dir", tmp_path)
        importlib.reload(cmk.fetchers.controller)

    # TODO (sk): rework this test - simplify parametrize and make individual tests
    @pytest.mark.parametrize("fetcher_name, fetcher_params, fetcher_class", [
        ("snmp", {
            "oid_infos": {},
            "use_snmpwalk_cache": False,
            "snmp_config": {
                "is_ipv6_primary": False,
                "hostname": "heute",
                "ipaddress": "127.0.0.1",
                "credentials": "public",
                "port": 161,
                "is_bulkwalk_host": False,
                "is_snmpv2or3_without_bulkwalk_host": False,
                "bulk_walk_size_of": 10,
                "timing": {},
                "oid_range_limits": [],
                "snmpv3_contexts": [],
                "character_encoding": None,
                "is_usewalk_host": False,
                "is_inline_snmp_host": False,
                "record_stats": False
            },
        }, SNMPDataFetcher),
        ("program", {
            "cmdline": "/bin/true",
            "stdin": None,
            "is_cmc": False,
        }, ProgramDataFetcher),
        ("tcp", {
            "family": socket.AF_INET,
            "address": "1.2.3.4",
            "timeout": 0.1,
            "encryption_settings": {
                "encryption": "settings"
            }
        }, TCPDataFetcher),
    ])
    @pytest.mark.usefixtures("scenario")
    def test_fetcher_factory(self, fetcher_name, fetcher_params, fetcher_class):
        ff = FetcherFactory()
        assert isinstance(ff.make(fetcher_name, fetcher_params), fetcher_class)

    @pytest.mark.parametrize("the_host", [
        "heute",
        "rrd_host",
    ])
    @pytest.mark.usefixtures("scenario")
    def test_run_fetchers(self, the_host, capsys):
        fetcher_config = core_cmc.FetcherConfig()
        fetcher_config.write(hostname=the_host)
        run_fetchers(serial=str(fetcher_config.serial), host_name=the_host, timeout=35)
        captured = capsys.readouterr()
        assert captured.out == make_success_answer("{}") + make_failure_answer(
            data="No process", hint="failed") + make_waiting_answer()


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
        assert Header.State.WAITING == "WAITING"
        assert Header.default_protocol_name() == "fetch"
