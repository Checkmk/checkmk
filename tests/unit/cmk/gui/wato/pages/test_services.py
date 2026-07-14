#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Generator

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.gui.http import request
from cmk.gui.wato.pages.services import DiscoveryPageRenderer
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.services import DiscoveryAction, DiscoveryOptions, DiscoveryState


def _changed_entry() -> CheckPreviewEntry:
    return CheckPreviewEntry(
        check_source=DiscoveryState.CHANGED,
        check_plugin_name="cpu_loads",
        ruleset_name="cpu_load",
        discovery_ruleset_name=None,
        item=None,
        old_discovered_parameters={},
        new_discovered_parameters={},
        effective_parameters={},
        description="CPU load",
        state=0,
        output="",
        metrics=[],
        old_labels={},
        new_labels={},
        found_on_nodes=[],
    )


def _discovery_options() -> DiscoveryOptions:
    return DiscoveryOptions(
        action=DiscoveryAction.NONE,
        show_checkboxes=False,
        show_parameters=False,
        show_discovered_labels=False,
        show_plugin_names=False,
        ignore_errors=True,
    )


@pytest.mark.usefixtures("request_context", "with_admin_login")
class TestDiscoveryPageRendererFolder:
    """The service discovery action menu must preserve the host's folder (CMK-35216).

    Hosts living in a subfolder used to trigger "The given host does not exist." when
    clicking any action menu entry, because the AJAX popup did not carry the folder.
    """

    @pytest.fixture
    def sub_host(self) -> Generator[Host]:
        root_folder = folder_tree().root_folder()
        sub = root_folder.create_subfolder(
            name="sub",
            title="",
            attributes={},
            pprint_value=False,
            use_git=False,
        )
        sub.create_hosts(
            [(HostName("sub_host"), {}, None)],
            pprint_value=False,
            use_git=False,
        )
        yield sub.load_host(HostName("sub_host"))
        self._cleanup_fs(root_folder)

    def _cleanup_fs(self, root_folder: Folder) -> None:
        shutil.rmtree(root_folder.filesystem_path(), ignore_errors=True)
        os.makedirs(root_folder.filesystem_path())

    def test_action_menu_url_vars_carry_the_hosts_folder(self, sub_host: Host) -> None:
        renderer = DiscoveryPageRenderer(host=sub_host, options=_discovery_options())

        url_vars = renderer._action_menu_url_vars("checkbox_name", _changed_entry())

        assert ("folder", "sub") in url_vars
        assert ("hostname", "sub_host") in url_vars

    def test_link_builders_point_to_the_hosts_folder(self, sub_host: Host) -> None:
        request.set_var("folder", "sub")
        request.set_var("host", "sub_host")

        rulesets_link = DiscoveryPageRenderer.rulesets_button_link("CPU load", "sub_host")
        assert "folder=sub" in rulesets_link
        assert "mode=object_parameters" in rulesets_link

        check_params_link = DiscoveryPageRenderer.check_parameters_button_link(
            _changed_entry(), "sub_host"
        )
        assert check_params_link is not None
        assert "folder=sub" in check_params_link
