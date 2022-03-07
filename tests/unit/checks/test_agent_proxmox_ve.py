#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_agent_proxmox_ve_arguments_password_store() -> None:

    params = {
        "username": "user",
        "password": ("password", "passwd"),
        "instance": "test",
        "protocol": "https",
    }
    agent = SpecialAgent("agent_proxmox_ve")
    assert agent.argument_func(params, "testhost", "1.2.3.4") == [
        "-u",
        "user",
        "-p",
        "passwd",
        "testhost",
    ]
