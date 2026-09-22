#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

import cmk.utils.paths
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.setup_git_test_helper import (
    init_setup_git_repo,
    setup_git_commit_subjects,
)
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK


@pytest.mark.usefixtures("with_admin_login")
def test_list_hosts_does_not_commit_the_setup_git_repo(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    config_dir = cmk.utils.paths.default_config_dir
    init_setup_git_repo(config_dir)
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("hosts", [])
    mock_livestatus.expect_query(["GET hosts", "Columns: name"], match_type="loose")

    with set_config(wato_use_git=True), mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/1.0/domain-types/host/collections/all",
            params=json.dumps({"columns": ["name"]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == 200, resp.text
    assert setup_git_commit_subjects(config_dir) == ["Initialized GIT for Checkmk"]
