#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from kubernetes.client import ApiClient  # type: ignore[import] # pylint: disable=import-error
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.api_server import RawAPI


def kubernetes_api_client():
    config = client.Configuration()
    config.host = "http://api-unittest"
    return ApiClient(config)


@pytest.fixture(name="raw_api")
def _raw_api():
    return RawAPI(kubernetes_api_client(), timeout=(10, 10))


def test_raw_api_get_healthz_ok(raw_api):
    Entry.single_register(Entry.GET, "http://api-unittest/some_health_endpoint", body="response-ok")
    with Mocketizer():
        result = raw_api._get_healthz("/some_health_endpoint")

    assert result.status_code == 200
    assert result.response == "response-ok"
    assert result.verbose_response is None


def test_raw_api_get_healthz_nok(raw_api):
    Entry.single_register(
        Entry.GET, "http://api-unittest/some_health_endpoint", body="response-nok", status=500
    )
    Entry.single_register(
        Entry.GET,
        "http://api-unittest/some_health_endpoint?verbose=1",
        body="verbose\nresponse\nnok",
        status=500,
    )
    with Mocketizer():
        result = raw_api._get_healthz("/some_health_endpoint")

    assert result.status_code == 500
    assert result.response == "response-nok"
    assert result.verbose_response == "verbose\nresponse\nnok"


def test_version_endpoint(raw_api):
    version_json = {
        "major": "1",
        "minor": "22",
        "gitVersion": "v1.22.2",
        "gitCommit": "8b5a19147530eaac9476b0ab82980b4088bbc1b2",
        "gitTreeState": "clean",
        "buildDate": "2021-09-15T21:32:41Z",
        "goVersion": "go1.16.8",
        "compiler": "gc",
        "platform": "linux/amd64",
    }
    Entry.single_register(
        Entry.GET,
        "http://api-unittest/version",
        body=json.dumps(version_json),
        headers={"content-type": "application/json"},
    )
    with Mocketizer():
        version = raw_api.query_version()
    assert version == "v1.22.2"
