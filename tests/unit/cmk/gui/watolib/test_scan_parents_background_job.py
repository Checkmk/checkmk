#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib
import shutil
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from livestatus import SiteId

from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.user import UserId

from cmk.automations.results import Gateway, GatewayResult, ScanParentsResult

from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib.hosts_and_folders import folder_tree, Host
from cmk.gui.watolib.parent_scan import (
    ParentScanBackgroundJob,
    ParentScanSettings,
    start_parent_scan,
)


@pytest.fixture(name="host")
def _host(with_admin_login: UserId, load_config: None) -> Iterator[Host]:
    # Ensure we have clean folder/host caches
    tree = folder_tree()
    tree.invalidate_caches()

    hostname = HostName("host1")
    root = folder_tree().root_folder()
    root.create_hosts([(hostname, {"site": SiteId(hostname)}, None)])
    host = root.host(hostname)
    assert host, "Test setup failed, host not created"

    yield host

    # Cleanup WATO folders created by the test
    tree_folder = pathlib.Path(tree.root_folder().filesystem_path())
    shutil.rmtree(tree_folder, ignore_errors=True)
    tree_folder.mkdir(parents=True, exist_ok=True)


@pytest.mark.usefixtures("inline_background_jobs")
def test_scan_parents_job(
    suppress_bake_agents_in_background: MagicMock, mocker: MockerFixture, host: Host
) -> None:
    # GIVEN
    scan_parents_mock = mocker.patch("cmk.gui.watolib.parent_scan.scan_parents")
    scan_parents_mock.return_value = ScanParentsResult(
        results=[GatewayResult(Gateway(None, HostAddress("123.0.0.1"), None), "gateway", 0, "")]
    )

    settings = ParentScanSettings(
        where="there",
        alias="alias",
        timeout=1,
        probes=2,
        max_ttl=3,
        force_explicit=True,
        ping_probes=4,
        gateway_folder_path=None,
    )

    # WHEN
    start_parent_scan(hosts=[host], job=ParentScanBackgroundJob(), settings=settings)

    # THEN
    with application_and_request_context():
        updated_host = folder_tree().root_folder().host(host.name())
        assert updated_host is not None and updated_host.parents() == [f"gw-{host.id()}-123-0-0-1"]

    suppress_bake_agents_in_background.assert_called_once_with([f"gw-{host.id()}-123-0-0-1"])
