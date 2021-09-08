#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents.agent_activemq import parse_arguments


def test_parse_arguments() -> None:
    args = parse_arguments(
        [
            "myserver",
            "8161",
            "--protocol",
            "https",
            "--piggyback",
            "--username",
            "abc",
            "--password",
            "123",
        ]
    )
    assert args.servername == "myserver"
    assert args.port == 8161
    assert args.username == "abc"
    assert args.password == "123"
    assert args.piggyback is True
    assert args.protocol == "https"
