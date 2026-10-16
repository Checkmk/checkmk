#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from http import HTTPStatus

import pytest
import responses

from cmk.special_agents.agent_pure_storage_fa import (
    agent_pure_storage_fa,
    parse_arguments,
)

API = "https://flasharray/api"


@pytest.fixture(name="api")
def _api() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as api:
        api.post(f"{API}/2.0/login", headers={"x-auth-token": "token"})
        api.get(f"{API}/api_version", json={"version": ["2.0", "2.2"]})
        yield api


def test_failed_section_is_skipped(
    api: responses.RequestsMock, capsys: pytest.CaptureFixture[str]
) -> None:
    api.get(f"{API}/2.2/arrays", json={"items": ["array"]})
    api.get(f"{API}/2.2/volumes", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    api.get(f"{API}/2.2/hardware", json={"items": ["hardware"]})
    api.get(f"{API}/2.2/alerts", json={"items": ["alert"]})

    assert agent_pure_storage_fa(parse_arguments(["--api-token", "secret", "flasharray"])) == 0

    assert capsys.readouterr().out.splitlines() == [
        "<<<pure_storage_fa_arrays:sep(0)>>>",
        json.dumps({"items": ["array"]}),
        "<<<pure_storage_fa_hardware:sep(0)>>>",
        json.dumps({"items": ["hardware"]}),
        "<<<pure_storage_fa_alerts:sep(0)>>>",
        json.dumps({"items": ["alert"]}),
    ]
