#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents.agent_activemq import parse_arguments


def test_parse_arguments() -> None:
    args = parse_arguments([
        '--servername',
        'myserver',
        '--port',
        '8161',
        '--protocol',
        'https',
        '--piggyback',
        '--username',
        'abc',
        '--password',
        '123',
    ])
    assert args.opt_servername == "myserver"
    assert args.opt_port == "8161"
    assert args.opt_username == "abc"
    assert args.opt_password == "123"
    assert args.opt_piggyback_mode is True
    assert args.opt_protocol == "https"
