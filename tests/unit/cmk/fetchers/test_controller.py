#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest  # type: ignore[import]

from cmk.utils.paths import core_helper_config_dir
from cmk.utils.type_defs import ConfigSerial

from cmk.fetchers.controller import (
    GlobalConfig,
    make_global_config_path,
    make_local_config_path,
    write_bytes,
)
from cmk.fetchers.protocol import CMCMessage
from cmk.fetchers.snmp import SNMPPluginStore


class TestGlobalConfig:
    @pytest.fixture
    def global_config(self):
        return GlobalConfig(
            cmc_log_level=5,
            cluster_max_cachefile_age=90,
            snmp_plugin_store=SNMPPluginStore(),
        )

    def test_deserialization(self, global_config):
        assert GlobalConfig.deserialize(global_config.serialize()) == global_config


class TestControllerApi:
    def test_controller_log(self):
        assert CMCMessage.log_answer(
            "payload",
            logging.WARNING,
        ) == b"fetch:LOG    :warning :7               :payload"

    def test_controller_end_of_reply(self):
        assert CMCMessage.end_of_reply() == b"fetch:ENDREPL:        :0               :"

    def test_make_local_config_path(self):
        assert make_local_config_path(
            serial=ConfigSerial("_serial_"),
            host_name="host",
        ) == core_helper_config_dir / "_serial_" / "fetchers" / "hosts" / "host.json"

    def test_make_global_config_path(self):
        assert make_global_config_path(serial=ConfigSerial(
            "_serial_"),) == core_helper_config_dir / "_serial_" / "fetchers" / "global_config.json"

    def test_write_bytes(self, capfdbinary):
        write_bytes(b"123")
        captured = capfdbinary.readouterr()
        assert captured.out == b"123"
        assert captured.err == b""
