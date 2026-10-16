#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from http import HTTPStatus

import pytest
import responses

from cmk.special_agents.agent_splunk import main

URL = "https://splunk:8089/services/licenser"
ARGS = [
    "--user",
    "user",
    "--password",
    "secret",
    "--modules",
    "license_state license_usage",
    "splunk",
]


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as api:
        api.get(f"{URL}/licenses", json={"entry": []})
        yield api


def test_failed_request_is_reported(api: responses.RequestsMock) -> None:
    api.get(f"{URL}/usage", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    assert main(ARGS) == 1


def test_unexpected_error_is_reported(api: responses.RequestsMock) -> None:
    api.get(f"{URL}/usage", json={"entry": [{"content": {}}]})
    assert main(ARGS) == 1
