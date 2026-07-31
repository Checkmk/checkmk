#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.gui.agent_download import _pages
from cmk.gui.agent_download._pages import (
    DOWNLOAD_AGENT_PLUGIN_PAGE,
    download_href,
    DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE,
    ModeDownloadAgentsOther,
    PageDownloadAgentPlugin,
    PluginFamilyDir,
)
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request as global_request
from cmk.gui.pages import PageContext


def _shipped_page(allowed_dirs: Sequence[Path]) -> PageDownloadAgentPlugin:
    return PageDownloadAgentPlugin(
        [p for p in allowed_dirs if not p.is_relative_to(cmk.utils.paths.local_root)],
        require_permission=False,
    )


def _local_page(allowed_dirs: Sequence[Path]) -> PageDownloadAgentPlugin:
    return PageDownloadAgentPlugin(allowed_dirs, require_permission=True)


def test_download_href_static_file_uses_apache_alias(request_context: None) -> None:
    path = str(cmk.utils.paths.agents_dir / "linux" / "check-mk-agent.rpm")
    assert download_href(path) == "agents/linux/check-mk-agent.rpm"


def test_download_href_plugin_family_file_uses_gui_handler(request_context: None) -> None:
    # A plugin family file lives outside share/check_mk/agents and must not be
    # served as a broken relative "agents/<absolute path>" URL.
    path = str(cmk.utils.paths.lib_dir / "python3/cmk/plugins/oracle/agents/mk-oracle")
    href = download_href(path)

    assert href.startswith(f"{DOWNLOAD_AGENT_PLUGIN_PAGE}.py?")
    assert "agents//" not in href


def test_download_href_local_plugin_family_file_uses_authenticated_handler(
    request_context: None,
) -> None:
    local_dir = cmk.utils.paths.local_lib_dir / "python3/cmk/plugins/custom/agents"

    href = download_href(str(local_dir / "mk-custom"))

    assert href.startswith(f"{DOWNLOAD_LOCAL_AGENT_PLUGIN_PAGE}.py?")


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

    mock_user = mocker.patch.object(_pages, "user")
    mock_response = mocker.patch.object(_pages, "response")
    mock_response.headers = {}

    page_context.request.set_var("path", str(plugin_file))
    _shipped_page([plugin_agents_dir]).page(page_context)

    # Shipped plugin files are served just like the statically served agent files:
    # without a login, hence also without a permission check.
    mock_user.need_permission.assert_not_called()
    mock_response.set_content_type.assert_called_once_with("application/octet-stream")
    mock_response.set_data.assert_called_once_with(b"binary payload")
    assert mock_response.headers["Content-Disposition"] == 'attachment; filename="mk-oracle"'


def test_page_download_local_requires_permission(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    local_agents_dir = tmp_path / "local" / "custom" / "agents"
    local_agents_dir.mkdir(parents=True)
    plugin_file = local_agents_dir / "mk-custom"
    plugin_file.write_bytes(b"local payload")

    mock_user = mocker.patch.object(_pages, "user")
    mock_response = mocker.patch.object(_pages, "response")
    mock_response.headers = {}

    page_context.request.set_var("path", str(plugin_file))
    _local_page([local_agents_dir]).page(page_context)

    mock_user.need_permission.assert_called_once_with("wato.download_agents")
    mock_response.set_data.assert_called_once_with(b"local payload")


def test_page_download_unauthenticated_rejects_local_plugin_file(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    shipped_agents_dir = tmp_path / "oracle" / "agents"
    shipped_agents_dir.mkdir(parents=True)
    local_agents_dir = tmp_path / "local" / "custom" / "agents"
    local_agents_dir.mkdir(parents=True)
    local_file = local_agents_dir / "mk-custom"
    local_file.write_bytes(b"local payload")

    mocker.patch.object(_pages, "user")

    page_context.request.set_var("path", str(local_file))
    with pytest.raises(MKUserError, match="not available for download"):
        _shipped_page([shipped_agents_dir]).page(page_context)


def test_page_download_local_rejects_shipped_plugin_file(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    shipped_agents_dir = tmp_path / "oracle" / "agents"
    shipped_agents_dir.mkdir(parents=True)
    shipped_file = shipped_agents_dir / "mk-oracle"
    shipped_file.write_bytes(b"binary payload")
    local_agents_dir = tmp_path / "local" / "custom" / "agents"
    local_agents_dir.mkdir(parents=True)

    mocker.patch.object(_pages, "user")

    page_context.request.set_var("path", str(shipped_file))
    with pytest.raises(MKUserError, match="not available for download"):
        _local_page([local_agents_dir]).page(page_context)


def test_page_download_rejects_traversal_outside_allowed_dirs(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    plugin_agents_dir = tmp_path / "oracle" / "agents"
    plugin_agents_dir.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"top secret")

    mocker.patch.object(_pages, "user")

    page_context.request.set_var("path", str(secret))
    with pytest.raises(MKUserError, match="not available for download"):
        _shipped_page([plugin_agents_dir]).page(page_context)


def test_page_download_rejects_missing_file(
    page_context: PageContext,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    plugin_agents_dir = tmp_path / "oracle" / "agents"
    plugin_agents_dir.mkdir(parents=True)

    mocker.patch.object(_pages, "user")

    page_context.request.set_var("path", str(plugin_agents_dir / "does-not-exist"))
    with pytest.raises(MKUserError, match="does not exist"):
        _shipped_page([plugin_agents_dir]).page(page_context)


@pytest.fixture(name="uncached_plugin_family_agents")
def fixture_uncached_plugin_family_agents() -> Iterator[None]:
    """Drop the process wide discovery cache around a test that patches the discovery.

    Clearing it upfront keeps the real families found at import time from shadowing the
    patched ones, clearing it afterwards keeps the patched ones out of later tests.
    """
    _pages._plugin_family_agents.cache_clear()
    try:
        yield
    finally:
        _pages._plugin_family_agents.cache_clear()


def test_plugin_family_agents_groups_shipped_and_local_dirs_of_one_family(
    uncached_plugin_family_agents: None,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        _pages,
        "discover_families",
        return_value={
            "cmk.plugins.oracle": [
                # A family can be installed locally in addition to being shipped.
                f"{cmk.utils.paths.local_lib_dir}/python3/cmk/plugins/oracle",
                f"{cmk.utils.paths.lib_dir}/python3/cmk/plugins/oracle",
            ],
            "cmk.plugins.custom": [f"{cmk.utils.paths.local_lib_dir}/python3/cmk/plugins/custom"],
        },
    )

    assert {
        family.title: [d.is_local for d in family.dirs] for family in _pages._plugin_family_agents()
    } == {
        # Both directories belong to one family, the shipped one first.
        "Oracle": [False, True],
        "Custom": [True],
    }


def test_other_mode_shows_shipped_and_local_file_in_one_section(
    request_context: None,
    mocker: MockerFixture,
    test_edition: cmk_version.Edition,
    tmp_path: Path,
) -> None:
    shipped_dir = tmp_path / "plugins" / "oracle" / "agents"
    shipped_dir.mkdir(parents=True)
    (shipped_dir / "mk_oracle").touch()
    (shipped_dir / "mk_oracle.ps1").touch()
    local_dir = tmp_path / "local" / "plugins" / "oracle" / "agents"
    local_dir.mkdir(parents=True)
    (local_dir / "mk_oracle").touch()

    mocker.patch.object(
        _pages,
        "_plugin_family_agents",
        return_value=[
            _pages.PluginFamilyAgents(
                title="Oracle",
                dirs=[
                    PluginFamilyDir(path=shipped_dir, is_local=False),
                    PluginFamilyDir(path=local_dir, is_local=True),
                ],
            )
        ],
    )

    sections = list(
        ModeDownloadAgentsOther(
            test_edition, PageContext(config=Config(), request=global_request)
        )._extra_sections()
    )

    # One section for the family, with the locally installed version of a file right
    # below the shipped one - and marked as the only one requiring a login.
    assert sections == [
        (
            "Oracle",
            [
                _pages.DownloadFile(str(shipped_dir / "mk_oracle"), "mk_oracle"),
                _pages.DownloadFile(
                    str(local_dir / "mk_oracle"), "mk_oracle (local, download requires login)"
                ),
                _pages.DownloadFile(str(shipped_dir / "mk_oracle.ps1"), "mk_oracle.ps1"),
            ],
        )
    ]


def test_other_mode_titles_share_tree_section_by_path(
    request_context: None,
    test_edition: cmk_version.Edition,
) -> None:
    # Files below the share tree keep their existing label.
    assert (
        ModeDownloadAgentsOther(
            test_edition, PageContext(config=Config(), request=global_request)
        )._title_for_root("/omd/share/check_mk/agents/plugins", "/plugins")
        == "Plug-ins"
    )
