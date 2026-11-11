#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The internal agent deployment endpoints on a site of the Community edition

The agent receiver calls them on a site of every edition. It reports a URL that matches no
endpoint as 501 to the agent controller, which then stops asking this site for agent updates.
"""

from http import HTTPStatus

from tests.testlib.unit.gui.gui_session_endpoints import internal_token_header
from tests.testlib.unit.rest_api_client import ClientRegistry

HOST_NAME = "my-host"
CONTROLLER_UUID = "34e4c967-1591-4883-8cdf-0e335b09618d"


def test_status_matches_no_endpoint_of_the_community_edition(clients: ClientRegistry) -> None:
    """TC-AU-002: the Community edition answers a status request like any unknown URL"""
    response = clients.AgentDeploymentInternal.status(
        HOST_NAME,
        {"uuid": CONTROLLER_UUID, "platform": "linux_deb", "installed_aghash": "fedcba9876543210"},
        headers=internal_token_header(),
        expect_ok=False,
    )

    response.assert_status_code(HTTPStatus.NOT_FOUND)
    assert response.json["title"] == "Not Found"


def test_download_matches_no_endpoint_of_the_community_edition(clients: ClientRegistry) -> None:
    """TC-AU-002: the Community edition answers a download request like any unknown URL"""
    response = clients.AgentDeploymentInternal.download(
        HOST_NAME,
        {"uuid": CONTROLLER_UUID, "platform": "linux_deb", "aghash": "0123456789abcdef"},
        headers=internal_token_header(),
        expect_ok=False,
    )

    response.assert_status_code(HTTPStatus.NOT_FOUND)
    assert response.json["title"] == "Not Found"
