#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterable

import pytest

import cmk.update_config.plugins.actions.remove_invalid_host
from cmk.automations.results import DeleteHostsResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.remove_invalid_host import RemoveInvalidHost


@pytest.fixture
def mock_delete_host_automation(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setattr(
        cmk.update_config.plugins.actions.remove_invalid_host,
        cmk.update_config.plugins.actions.remove_invalid_host.delete_hosts.__name__,  # type: ignore[attr-defined]
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    yield


@pytest.mark.usefixtures("mock_delete_host_automation")
def test_remove_invalid_host(with_admin_login: UserId, load_config: None) -> None:
    hostname = HostName("")
    root = folder_tree().root_folder()
    root.create_hosts(
        [(hostname, HostAttributes(site=SiteId("NO_SITE")), None)],
        pprint_value=False,
        use_git=False,
    )
    host = root.host(hostname)
    assert host, "Test setup failed, host not created"

    RemoveInvalidHost(
        name="remove_invalid_host",
        title="Remove invalid host",
        sort_index=155,
        expiry_version=ExpiryVersion.CMK_300,
    )(logging.getLogger())

    root = folder_tree().root_folder()
    host = root.host(hostname)
    assert not host, "Invalid host not deleted"
