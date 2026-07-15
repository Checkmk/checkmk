#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import cmk.utils.paths
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request as global_request
from cmk.gui.pages import PageContext
from cmk.gui.wato.pages import download_agents
from cmk.gui.wato.pages.download_agents import (
    _download_href,
    DOWNLOAD_AGENT_PLUGIN_PAGE,
    PageDownloadAgentPlugin,
)


def test_download_href_static_file_uses_apache_alias(request_context: None) -> None:
    path = str(cmk.utils.paths.agents_dir / "linux" / "check-mk-agent.rpm")
    assert _download_href(path) == "agents/linux/check-mk-agent.rpm"


def test_download_href_plugin_family_file_uses_gui_handler(request_context: None) -> None:
    # A plugin family file lives outside share/check_mk/agents and must not be
    # served as a broken relative "agents/<absolute path>" URL.
    path = "/omd/sites/heute/lib/python3/cmk/plugins/oracle/agents/mk-oracle"
    href = _download_href(path)

    assert href.startswith(f"{DOWNLOAD_AGENT_PLUGIN_PAGE}.py?")
    assert "agents//omd" not in href


@pytest.fixture(name="page_context")
def fixture_page_context(request_context: None) -> PageContext:
    return PageContext(config=Config(), request=global_request)


def test_page_download_serves_allowed_plugin_file(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    plugin_agents_dir = tmp_path / "oracle" / "agents"
    plugin_agents_dir.mkdir(parents=True)
    plugin_file = plugin_agents_dir / "mk-oracle"
    plugin_file.write_bytes(b"binary payload")

    mocker.patch.object(
        download_agents, "_plugin_family_agent_dirs", return_value=[plugin_agents_dir]
    )
    mock_user = mocker.patch.object(download_agents, "user")
    mock_response = mocker.patch.object(download_agents, "response")
    mock_response.headers = {}

    page_context.request.set_var("path", str(plugin_file))
    PageDownloadAgentPlugin().page(page_context)

    mock_user.need_permission.assert_called_once_with("wato.download_agents")
    mock_response.set_content_type.assert_called_once_with("application/octet-stream")
    mock_response.set_data.assert_called_once_with(b"binary payload")
    assert mock_response.headers["Content-Disposition"] == 'attachment; filename="mk-oracle"'


def test_page_download_rejects_traversal_outside_allowed_dirs(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    plugin_agents_dir = tmp_path / "oracle" / "agents"
    plugin_agents_dir.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"top secret")

    mocker.patch.object(
        download_agents, "_plugin_family_agent_dirs", return_value=[plugin_agents_dir]
    )
    mocker.patch.object(download_agents, "user")

    page_context.request.set_var("path", str(secret))
    with pytest.raises(MKUserError, match="not available for download"):
        PageDownloadAgentPlugin().page(page_context)


def test_page_download_rejects_missing_file(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    plugin_agents_dir = tmp_path / "oracle" / "agents"
    plugin_agents_dir.mkdir(parents=True)

    mocker.patch.object(
        download_agents, "_plugin_family_agent_dirs", return_value=[plugin_agents_dir]
    )
    mocker.patch.object(download_agents, "user")

    page_context.request.set_var("path", str(plugin_agents_dir / "does-not-exist"))
    with pytest.raises(MKUserError, match="does not exist"):
        PageDownloadAgentPlugin().page(page_context)
