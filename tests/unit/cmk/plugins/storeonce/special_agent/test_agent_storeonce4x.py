#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json

import pytest
import responses
import time_machine

from cmk.password_store.v1_unstable import Secret
from cmk.plugins.storeonce.special_agent.agent_storeonce4x import (
    agent_storeonce4x_main,
    parse_arguments,
    StoreOnceOauth2Session,
)

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

# Minimal canned REST responses, keyed by the path each section requests.
_MEMBERS = {"members": [{"uuid": "uuid-1", "hostname": "appliance-1"}]}
_DASHBOARD = {"hostname": "appliance-1", "softwareVersion": "4.2.3"}
_CAT_STORES = {"members": [{"id": "store-1"}]}
_CAT_STORE = {"id": "store-1", "name": "store-one"}

_REST_RESPONSES = {
    "/api/v1/data-services/d2d-service/status": {"services": {}},
    "/api/v1/data-services/rep/services": {"services": {}},
    "/api/v1/data-services/vtl/services": {"services": {}},
    "/rest/alerts": {},
    "/api/v1/management-services/system/information": {"productName": "StoreOnce"},
    "/api/v1/management-services/local-storage/overview": {"capacityBytes": 1},
    "/api/v1/management-services/federation/members": _MEMBERS,
    "/api/v1/data-services/dashboard/appliance/uuid-1": _DASHBOARD,
    "/api/v1/management-services/licensing": {"summary": "ok"},
    "/api/v1/management-services/licensing/licenses": {"licenses": []},
    "/api/v1/data-services/cat/stores": _CAT_STORES,
    "/api/v1/data-services/cat/stores/store/store-1": _CAT_STORE,
}

# How many JSON lines every section is expected to emit.
_EXPECTED_LINE_COUNTS = {
    "d2d_services": 1,
    "rep_services": 1,
    "vtl_services": 1,
    "alerts": 1,
    "system_information": 1,
    "storage": 1,
    "appliances": 2,
    "licensing": 2,
    "cat_stores": 2,
}


def _register_rest_responses() -> None:
    responses.add(
        responses.POST,
        f"https://{HOST}:{PORT}/pml/login/authenticate",
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )
    for path, payload in _REST_RESPONSES.items():
        responses.add(
            responses.GET,
            f"https://{HOST}:{PORT}{path}",
            json=payload,
            status=200,
        )


def _parse_agent_output(output: str) -> dict[str, list[str]]:
    """Split raw agent output into {section_basename: [data lines]}."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in output.splitlines():
        if line.startswith("<<<") and line.endswith(">>>"):
            current = line[3:-3].split(":", 1)[0].removeprefix("storeonce4x_")
            sections[current] = []
        elif current is not None and line:
            sections[current].append(line)
    return sections


@responses.activate
@time_machine.travel(NOW_SIMULATED, tick=False)
def test_invalid_tokenfile() -> None:  # not sure what this meant to test. There is no token file.
    responses.add(
        responses.POST,
        f"https://{HOST}:{PORT}/pml/login/authenticate",
        json=TOKEN_JSON_FROM_STOREONCE,
        status=200,
    )

    mysession = StoreOnceOauth2Session(HOST, PORT, "user", Secret("secret"), False)

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
    mysession = StoreOnceOauth2Session(HOST, PORT, "user", Secret("secret"), False)
    resp = mysession.get("/api/v1/data-services/d2d-service/status")

    assert resp["random_answer"] == "foo-bar"


@time_machine.travel(NOW_SIMULATED, tick=False)
@responses.activate
def test_agent_storeonce4x_main_serializes_sections_line_by_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _register_rest_responses()

    return_code = agent_storeonce4x_main(
        parse_arguments(["--user", USER, "--password", SECRET, "-p", PORT, HOST])
    )

    assert return_code == 0

    sections = _parse_agent_output(capsys.readouterr().out)

    # Every section was emitted, in the order defined by SECTIONS.
    assert list(sections) == list(_EXPECTED_LINE_COUNTS)

    for name, lines in sections.items():
        # Each section produced the expected number of data lines
        assert len(lines) == _EXPECTED_LINE_COUNTS[name], name
        for line in lines:
            assert isinstance(json.loads(line), dict)


@time_machine.travel(NOW_SIMULATED, tick=False)
@responses.activate
def test_agent_storeonce4x_main_nested_section_yields_members_and_details(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A nested section writes the member list first, then one line per member."""
    _register_rest_responses()

    agent_storeonce4x_main(
        parse_arguments(["--user", USER, "--password", SECRET, "-p", PORT, HOST])
    )

    appliances = _parse_agent_output(capsys.readouterr().out)["appliances"]

    assert [json.loads(line) for line in appliances] == [_MEMBERS, _DASHBOARD]
