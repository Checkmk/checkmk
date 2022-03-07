#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_agent_jira_arguments_password_store() -> None:

    params = {
        "user": "username",
        "password": ("password", "passwd"),
        "instance": "test",
        "protocol": "https",
    }
    agent = SpecialAgent("agent_jira")
    assert agent.argument_func(params, "test", "1.2.3.4") == [
        "-P",
        "https",
        "-u",
        "username",
        "-s",
        "passwd",
        "--hostname",
        "test",
    ]
