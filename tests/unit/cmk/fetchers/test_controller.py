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
    GlobalConfig,
    make_global_config_path,
    make_local_config_path,
    run_fetcher,
    write_bytes,
)
from cmk.fetchers.protocol import CMCLogLevel, make_end_of_reply_answer, make_log_answer
from cmk.fetchers.type_defs import Mode


class TestGlobalConfig:
    @pytest.fixture
    def global_config(self):
        return GlobalConfig(log_level=5)

    def test_deserialization(self, global_config):
        assert GlobalConfig.deserialize(global_config.serialize()) == global_config


class TestControllerApi:
    def test_controller_log(self):
        assert make_log_answer(
            "payload",
            logging.WARNING,
        ) == b"fetch:LOG    :warning :7       :payload"

    def test_controller_end_of_reply(self):
        assert make_end_of_reply_answer() == b"fetch:ENDREPL:        :0       :"

    def test_local_config_path(self):
        assert make_local_config_path(
            serial=ConfigSerial("_serial_"),
            host_name="buzz",
        ) == (core_helper_config_dir / "_serial_" / "fetchers" / "hosts" / "buzz.json")

    def test_global_config_path(self):
        assert make_global_config_path(serial=ConfigSerial(
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
