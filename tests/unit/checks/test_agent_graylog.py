#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_agent_graylog_arguments_password_store() -> None:

    agent = SpecialAgent("agent_graylog")
    params = {
        "user": "user",
        "password": ("password", "passwd"),
        "instance": "test",
        "protocol": "https",
        "sections": ["alerts"],
        "since": 1800,
        "display_node_details": "host",
        "display_sidecar_details": "host",
        "display_source_details": "host",
    }
    assert agent.argument_func(params, "testhost", "1.2.3.4") == [
        "-P",
        "https",
        "-m",
        "alerts",
        "-t",
        1800,
        "-u",
        "user",
        "-s",
        "passwd",
        "--display_node_details",
        "host",
        "--display_sidecar_details",
        "host",
        "--display_source_details",
        "host",
        "test",
    ]
