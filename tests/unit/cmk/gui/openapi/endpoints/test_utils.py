#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.gui import sites
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.openapi.endpoints.utils import get_site_id_for_host, may_fail
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.session_context import SuperUserContext
from cmk.livestatus_client.testing import MockLiveStatusConnection


def test_may_fail_catches_value_error() -> None:
    with (
        pytest.raises(ProblemException) as exc_info,
        may_fail(ValueError, status=HTTPStatus.NOT_FOUND),
    ):
        raise ValueError("Nothing to see here, move along.")
    data = json.loads(exc_info.value.to_problem().data)
    assert data["status"] == HTTPStatus.NOT_FOUND
    assert data["detail"] == "Nothing to see here, move along."


def test_may_fail_catches_mk_user_error() -> None:
    with pytest.raises(ProblemException) as exc_info, may_fail(MKUserError):
        raise MKUserError(
            None, "There is an activation already running.", status=HTTPStatus.CONFLICT
        )
    data = json.loads(exc_info.value.to_problem().data)
    assert data["status"] == HTTPStatus.CONFLICT
    assert data["detail"] == "There is an activation already running."


def test_may_fail_catches_mk_auth_exception() -> None:
    with (
        pytest.raises(ProblemException) as exc_info,
        may_fail(MKAuthException, status=HTTPStatus.UNAUTHORIZED),
    ):
        raise MKAuthException("These are not the droids that you are looking for.")
    data = json.loads(exc_info.value.to_problem().data)
    assert data["status"] == HTTPStatus.UNAUTHORIZED
    assert data["detail"] == "These are not the droids that you are looking for."


@pytest.mark.usefixtures("request_context")
def test_get_site_id_for_host_unknown_host(mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.add_table("hosts", [])
    with mock_livestatus(expect_status_query=True) as live, SuperUserContext():
        live.expect_query("GET hosts\nColumns: name\nFilter: name = nonexistent.example.com")
        with pytest.raises(ProblemException) as exc_info:
            get_site_id_for_host(sites.live(), "nonexistent.example.com")
    data = json.loads(exc_info.value.to_problem().data)
    assert data["status"] == HTTPStatus.NOT_FOUND
