#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.core_helpers.controller import GlobalConfig
from cmk.core_helpers.protocol import CMCMessage
from cmk.core_helpers.snmp import SNMPPluginStore


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
        assert (
            CMCMessage.log_answer(
                "payload",
                logging.WARNING,
            )
            == b"fetch:LOG    :warning :7               :payload"
        )

    def test_controller_end_of_reply(self):
        assert CMCMessage.end_of_reply() == b"fetch:ENDREPL:        :0               :"
