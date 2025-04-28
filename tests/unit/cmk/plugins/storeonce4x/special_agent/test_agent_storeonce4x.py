#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import responses
import time_machine

from cmk.plugins.storeonce4x.special_agent.agent_storeonce4x import StoreOnceOauth2Session

#   .--defines-------------------------------------------------------------.
#   |                      _       __ _                                    |
#   |                   __| | ___ / _(_)_ __   ___  ___                    |
#   |                  / _` |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | (_| |  __/  _| | | | |  __/\__ \                   |
#   |                  \__,_|\___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
PORT = "1111"
HOST = "myhost"
USER = "user"
SECRET = "top-secret"

NOW_SIMULATED = "1988-06-08 17:00:00.000000"

EXPIRES_IN = 30
TOKEN_JSON_FROM_STOREONCE = {
    "expires_in": EXPIRES_IN,
    "refresh_token": "123456789",
    "access_token": "105190b1-2497-440c-8f55-c4a4f466bfc7",
    "scope": "not-implemented",
    "sessionID": "9876543421",
    "userName": "user",
}


@responses.activate
@time_machine.travel(NOW_SIMULATED, tick=False)
def test_invalid_tokenfile() -> None:
    responses.add(
        responses.POST,
        f"https://{HOST}:{PORT}/pml/login/authenticate",
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )

    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)

    assert mysession._json_token["expires_in"] == EXPIRES_IN
    assert mysession._json_token["expires_in_abs"] == "1988-06-08 17:00:10.000000"


@time_machine.travel(NOW_SIMULATED, tick=False)
@responses.activate
def test_REST_call() -> None:
    responses.add(
        responses.POST,
        f"https://{HOST}:{PORT}/pml/login/authenticate",
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )
    responses.add(responses.GET, f"https://{HOST}:{PORT}/rest/alerts/", json={}, status=200)
    responses.add(
        responses.GET,
        f"https://{HOST}:{PORT}/api/v1/data-services/d2d-service/status",
        json={
            "random_answer": "foo-bar",
        },
        status=200,
    )
    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)
    resp = mysession.get("/api/v1/data-services/d2d-service/status")

    assert resp["random_answer"] == "foo-bar"
