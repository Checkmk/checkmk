#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_agent_proxmox_ve_arguments_password_store() -> None:

    params = {
        "username": "user",
        "password": ("password", "passwd"),
        "port": "443",
        "no-cert-check": True,
        "timeout": "30",
        "log-cutoff-weeks": "4",
    }
    agent = SpecialAgent("agent_proxmox_ve")
    assert agent.argument_func(params, "testhost", "1.2.3.4") == [
        "-u",
        "user",
        "-p",
        "passwd",
        "--port",
        "443",
        "--no-cert-check",
        "--timeout",
        "30",
        "--log-cutoff-weeks",
        "4",
        "testhost",
    ]
