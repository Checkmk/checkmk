#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
import responses  # type: ignore[import]
from cmk.special_agents.agent_cisco_prime import main

AUTH = ("user", "passw0rd")
HOST = "httpbin.org"


def test_wrong_arguments(capsys):
    with pytest.raises(SystemExit):
        main([])
    assert capsys.readouterr().out == ''


@responses.activate
def test_agent_output(capsys):
    responses.add(
        responses.GET,
        "https://%s/basic-auth/%s/%s" % (HOST, *AUTH),
        json={
            "authenticated": True,
            "user": "user"
        },
        status=200,
    )
    main(["--hostname", HOST, "--path", "basic-auth/%s/%s" % AUTH, "-u", "%s:%s" % AUTH])
    assert capsys.readouterr() == (
        '<<<cisco_prime_wifi_connections:sep(0)>>>\n{"authenticated": true, "user": "user"}\n',
        '',
    )


@responses.activate
def test_missing_credentials(capsys):
    responses.add(
        responses.GET,
        "https://%s/basic-auth/%s/%s" % (HOST, *AUTH),
        status=401,
    )
    with pytest.raises(SystemExit):
        main(["--hostname", HOST, "--path", "basic-auth/%s/%s" % AUTH])
    assert capsys.readouterr() == (
        '',
        '401 Client Error: Unauthorized for url: https://httpbin.org/basic-auth/user/passw0rd\n',
    )
