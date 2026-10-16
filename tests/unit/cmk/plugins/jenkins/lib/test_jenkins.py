#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from http import HTTPStatus

import pytest
import requests
import responses

from cmk.plugins.jenkins.lib.jenkins import agent_jenkins_main, parse_arguments

ARGS = ["--user", "user", "--password", "secret", "--sections", "instance,jobs", "jenkins"]
INSTANCE_URL = re.compile(r"https://jenkins:443/api/json\?tree=mode,.*")
JOBS_URL = re.compile(r"https://jenkins:443/api/json\?tree=jobs.*")


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as api:
        api.get(INSTANCE_URL, json={"mode": "NORMAL"})
        yield api


def test_failed_request_is_reported(api: responses.RequestsMock) -> None:
    api.get(JOBS_URL, status=HTTPStatus.FORBIDDEN)
    assert agent_jenkins_main(parse_arguments(ARGS)) != 0


def test_connection_error_is_reported(api: responses.RequestsMock) -> None:
    api.get(JOBS_URL, body=requests.ConnectionError("connection refused"))
    assert agent_jenkins_main(parse_arguments(ARGS)) != 0
