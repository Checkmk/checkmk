#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.web_test_app import WebTestAppForCMK

import cmk.ccc.version as cmk_version

from cmk.utils import paths


@pytest.mark.skipif(
    cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE,
    reason="No agent deployment in raw edition",
)
def test_deploy_agent(wsgi_app: WebTestAppForCMK) -> None:
    response = wsgi_app.get("/NO_SITE/check_mk/deploy_agent.py")
    assert response.json["result"].startswith("Missing or invalid")

    response = wsgi_app.get("/NO_SITE/check_mk/deploy_agent.py?mode=agent")
    assert response.json["result"].startswith("Missing host")


def test_download_agent_shipped_with_checkmk(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    agent_bin_data = bytes.fromhex("01 02 03 04 05")
    mocked_agent_path = tmp_path / "agent_bin_mock.deb"
    with open(mocked_agent_path, "wb") as fo:
        fo.write(agent_bin_data)

    packed_agent_path_patched = mocker.patch(
        "cmk.gui.openapi.endpoints.agent.agent.packed_agent_path_linux_deb",
        return_value=mocked_agent_path,
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/agent/actions/download/invoke?os_type=linux_deb",
        headers={"Accept": "application/octet-stream"},
        status=200,
    )

    assert resp.body == agent_bin_data
    assert resp.headers["Content-Disposition"] == 'attachment; filename="agent_bin_mock.deb"'
    packed_agent_path_patched.assert_called_once()


@pytest.mark.skipif(
    cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE,
    reason="endpoint not available in raw edition",
)
def test_openapi_agent_key_id_above_zero_regression(clients: ClientRegistry) -> None:
    # make sure this doesn't crash
    clients.Agent.bake_and_sign(key_id=0, passphrase="", expect_ok=False).assert_status_code(400)
