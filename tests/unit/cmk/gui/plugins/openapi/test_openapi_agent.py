#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest_mock import MockerFixture

import cmk.utils.version as cmk_version


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="No agent deployment in raw edition")
def test_deploy_agent(wsgi_app) -> None:
    response = wsgi_app.get("/NO_SITE/check_mk/deploy_agent.py")
    assert response.text.startswith("ERROR: Missing or invalid")

    response = wsgi_app.get("/NO_SITE/check_mk/deploy_agent.py?mode=agent")
    assert response.text.startswith("ERROR: Missing host")


def test_download_agent_shipped_with_checkmk(
    wsgi_app, with_automation_user, mocker: MockerFixture, tmp_path
):
    agent_bin_data = bytes.fromhex("01 02 03 04 05")
    mocked_agent_path = tmp_path / "agent_bin_mock.bin"
    with open(mocked_agent_path, "wb") as fo:
        fo.write(agent_bin_data)

    packed_agent_path_patched = mocker.patch(
        "cmk.gui.plugins.openapi.endpoints.agent.agent.packed_agent_path_linux_deb",
        return_value=mocked_agent_path,
    )

    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    resp = wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/agent/actions/download/invoke?os_type=linux_deb",
        headers={"Accept": "application/octet-stream"},
        status=200,
    )

    assert resp.body == agent_bin_data
    assert resp.headers["Content-Disposition"] == 'attachment; filename="agent_bin_mock.bin"'
    packed_agent_path_patched.assert_called_once()
