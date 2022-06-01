#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import responses  # type: ignore[import]
from freezegun import freeze_time

from cmk.special_agents.agent_storeonce4x import StoreOnceOauth2Session

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
@freeze_time(NOW_SIMULATED)
def test_invalid_tokenfile():

    responses.add(
        responses.POST,
        "https://%s:%s/pml/login/authenticate" % (HOST, PORT),
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )

    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)

    assert mysession._json_token["expires_in"] == EXPIRES_IN
    assert mysession._json_token["expires_in_abs"] == "1988-06-08 17:00:10.000000"


@freeze_time(NOW_SIMULATED)
@responses.activate
def test_REST_call():
    responses.add(
        responses.POST,
        "https://%s:%s/pml/login/authenticate" % (HOST, PORT),
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )
    responses.add(responses.GET, "https://%s:%s/rest/alerts/" % (HOST, PORT), json={}, status=200)
    responses.add(
        responses.GET,
        "https://%s:%s/api/v1/data-services/d2d-service/status" % (HOST, PORT),
        json={
            "random_answer": "foo-bar",
        },
        status=200,
    )
    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)
    resp = mysession.get("/api/v1/data-services/d2d-service/status")

    assert resp["random_answer"] == "foo-bar"
