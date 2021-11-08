#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import responses  # type: ignore[import]

from cmk.special_agents.agent_cisco_prime import main

AUTH = ("user", "passw0rd")
HOST = "httpbin.org"
API_PATH = "webacs/api/v1/data"
REQUESTS = (
    "AccessPoints.json?.full=true&.nocount=true&.maxResults=10000",
    "ClientCounts.json?.full=true&subkey=ROOT-DOMAIN&type=SSID",
    "WlanControllers.json?.full=true",
)


@pytest.fixture(name="accept_requests")
def fixture_accept_requests(return_code):
    for req in REQUESTS:
        responses.add(
            responses.GET,
            "https://%s/%s/%s" % (HOST, API_PATH, req),
            json={"authenticated": True, "user": "user"},
            status=return_code,
        )


def test_wrong_arguments(capsys):
    with pytest.raises(SystemExit):
        main([])
    assert capsys.readouterr().out == ""


@responses.activate
@pytest.mark.parametrize("return_code", [200])
def test_agent_output(capsys, accept_requests):
    main(["--debug", "--hostname", HOST, "-u", "%s:%s" % AUTH])
    assert capsys.readouterr() == (
        "<<<cisco_prime_wifi_access_points:sep(0)>>>\n"
        '{"authenticated": true, "user": "user"}\n'
        "<<<cisco_prime_wifi_connections:sep(0)>>>\n"
        '{"authenticated": true, "user": "user"}\n'
        "<<<cisco_prime_wlan_controller:sep(0)>>>\n"
        '{"authenticated": true, "user": "user"}\n',
        "",
    )


@responses.activate
@pytest.mark.parametrize("return_code", [401])
def test_missing_credentials(capsys, accept_requests):
    with pytest.raises(SystemExit):
        main(["--hostname", HOST])
    assert capsys.readouterr() == (
        "",
        "401 Client Error: Unauthorized for url: "
        "https://%s/%s/%s\n" % (HOST, API_PATH, REQUESTS[0]),
    )
