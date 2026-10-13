#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

import pytest
import responses

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.automations import get_url_raw, MKRemoteSiteUnavailable

_URL = "https://remote.example/remote/check_mk/automation.py"


@responses.activate
@pytest.mark.parametrize(
    "status, body",
    [
        pytest.param(HTTPStatus.SERVICE_UNAVAILABLE, "<h1>Site Not Started</h1>", id="not started"),
        pytest.param(HTTPStatus.BAD_GATEWAY, "Proxy Error", id="bad gateway"),
    ],
)
def test_unavailable_remote_site_is_reported_as_such(status: HTTPStatus, body: str) -> None:
    responses.post(_URL, status=status, body=body)

    with pytest.raises(MKRemoteSiteUnavailable):
        get_url_raw(_URL, insecure=False)


@responses.activate
def test_other_http_errors_are_not_reported_as_unavailable_site() -> None:
    responses.post(_URL, status=HTTPStatus.INTERNAL_SERVER_ERROR, body="Internal error")

    with pytest.raises(MKUserError) as excinfo:
        get_url_raw(_URL, insecure=False)

    assert not isinstance(excinfo.value, MKRemoteSiteUnavailable)
