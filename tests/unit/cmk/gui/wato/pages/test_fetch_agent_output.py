#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from tests.testlib.common.repo import repo_path

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.agentdatatype import AgentRawData

from cmk.automations.results import GetAgentOutputResult

from cmk.gui.wato.pages.fetch_agent_output import (
    FetchAgentOutputRequest,
    get_fetch_agent_job_status,
    get_fetch_agent_output_file,
    start_fetch_agent_job,
)
from cmk.gui.watolib.automations import LocalAutomationConfig
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host


@pytest.fixture(name="icon_dir")
def fixture_icon_dir() -> None:
    src_path = repo_path() / "packages/cmk-frontend/src/themes"
    target_path = cmk.utils.paths.web_dir / "htdocs/themes"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.symlink_to(src_path)


@pytest.fixture(name="host")
def fixture_host(with_admin_login: UserId, load_config: None) -> Iterator[Host]:
    tree = folder_tree()
    tree.invalidate_caches()

    hostname = HostName("host1")
    root = folder_tree().root_folder()
    root.create_hosts([(hostname, {"site": SiteId("NO_SITE")}, None)], pprint_value=False)
    host = root.host(hostname)
    assert host, "Test setup failed, host not created"
    yield host


@pytest.mark.usefixtures("inline_background_jobs", "icon_dir")
def test_fetch_agent_job(host: Host, mocker: MockerFixture) -> None:
    # GIVEN
    get_agent_output_mock = mocker.patch(
        "cmk.gui.wato.pages.fetch_agent_output.get_agent_output",
        return_value=GetAgentOutputResult(
            success=True,
            service_details="x",
            raw_agent_data=AgentRawData(b"y"),
        ),
    )

    # WHEN
    start_fetch_agent_job(request := FetchAgentOutputRequest(host, "agent"))

    # THEN
    get_agent_output_mock.assert_called_once_with(
        LocalAutomationConfig(), "host1", "agent", timeout=10, debug=False
    )
    job_status = get_fetch_agent_job_status(request)
    assert job_status.state == "finished", job_status
    assert get_fetch_agent_output_file(request) == b"y"
