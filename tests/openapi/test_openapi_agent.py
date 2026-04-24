#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pytest_mock import MockerFixture

from tests.testlib.gui.web_test_app import WebTestAppForCMK


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
