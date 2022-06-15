#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "client_id": "clientID",
                "url": "http://cloud.com",
                "vhm_id": "102",
                "redirect_url": "http://redirect.com",
                "api_token": "token",
                "client_secret": "clientsecret",
            },
            ["http://cloud.com", "102", "token", "clientID", "clientsecret", "http://redirect.com"],
            id="with explicit password",
        ),
        pytest.param(
            {
                "client_id": "clientID",
                "url": "http://cloud.com",
                "vhm_id": "102",
                "redirect_url": "http://redirect.com",
                "api_token": "token",
                "client_secret": ("store", "hivemanager_ng"),
            },
            [
                "http://cloud.com",
                "102",
                "token",
                "clientID",
                ("store", "hivemanager_ng", "%s"),
                "http://redirect.com",
            ],
            id="with password from store",
        ),
    ],
)
def test_hivemanager_ng_argument_parsing(
    params: Mapping[str, Any], expected_args: Sequence[Any]
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_hivemanager_ng")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
