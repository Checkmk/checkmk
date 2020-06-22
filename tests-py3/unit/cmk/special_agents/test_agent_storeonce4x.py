#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from mock import mock_open, patch, call
from freezegun import freeze_time  # type: ignore[import]
import responses  # type: ignore[import]
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
EXP_IN_ABS_SIMULATED = "1988-06-08 17:01:00.000000"
INVALID_TOKEN = "{\"I AM NOT A TOKEN FILE\":\"000\"}"
VALID_TOKEN = "{\"expires_in_abs\":\"%s\",\"expires_in\":\"2700\"," \
              "\"refresh_token\":\"0c91fcbf-8ca0-452d-be06-0d49446defcc\"," \
              "\"access_token\":\"105190b1-2497-440c-8f55-c4a4f466bfc7\"," \
              "\"sessionID\":\"6e608d07-0aa9-4a36-84ab-6be6f1dc5d89\"," \
              "\"userName\":\"user\"}" % EXP_IN_ABS_SIMULATED

EXPIRES_IN = '30'
TOKEN_JSON_FROM_STOREONCE = {
    'expires_in': EXPIRES_IN,
    'refresh_token': '123456789',
    'access_token': '105190b1-2497-440c-8f55-c4a4f466bfc7',
    'scope': 'not-implemented',
    'sessionID': '9876543421',
    'userName': 'user'
}


@patch("builtins.open", new_callable=mock_open, read_data=VALID_TOKEN)
@freeze_time(NOW_SIMULATED)
def test_tokenfile_exists(mock_file):

    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)
    assert mock_file.call_args == call('%s_oAuthToken.json' % HOST, 'r')
    assert mysession._json_token["expires_in"] == 60
    assert mysession._json_token["expires_in_abs"] == "1988-06-08 17:01:00.000000"


@patch("builtins.open", new_callable=mock_open, read_data=INVALID_TOKEN)
@responses.activate
@freeze_time(NOW_SIMULATED)
def test_invalid_tokenfile(mock_file):

    responses.add(responses.POST,
                  'https://%s:%s/pml/login/authenticate' % (HOST, PORT),
                  json=TOKEN_JSON_FROM_STOREONCE,
                  status=200)

    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)
    assert mock_file.call_args == call('myhost_oAuthToken.json', 'w')
    assert mysession._json_token["expires_in"] == EXPIRES_IN
    assert mysession._json_token["expires_in_abs"] == "1988-06-08 17:00:10.000000"


@patch("builtins.open", new_callable=mock_open, read_data=VALID_TOKEN)
@freeze_time(NOW_SIMULATED)
@responses.activate
def test_REST_call(mock_file):

    responses.add(responses.GET,
                  'https://%s:%s/api/v1/data-services/d2d-service/status' % (HOST, PORT),
                  json={
                      'random_answer': 'foo-bar',
                  },
                  status=200)
    mysession = StoreOnceOauth2Session(HOST, PORT, "user", "secret", False)
    resp = mysession.execute_get_request("/api/v1/data-services/d2d-service/status")

    assert resp.status_code == 200
    assert resp.json()['random_answer'] == 'foo-bar'
