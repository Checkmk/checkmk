#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import SpecialAgent


def test_agent_smb_share_arguments_password_store() -> None:
    params = {
        "authentication": ("user", ("password", "passwd")),
        "patterns": [],
    }
    agent = SpecialAgent("agent_smb_share")
    assert agent.argument_func(params, "testhost", "1.2.3.4") == [
        "testhost",
        "1.2.3.4",
        "--username",
        "user",
        "--password",
        "passwd",
    ]
