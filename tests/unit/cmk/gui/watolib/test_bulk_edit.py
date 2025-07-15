#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId

from cmk.gui.wato.pages._bulk_actions import _search_text_matches
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import FolderTree, Host


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_search_text_matches() -> None:
    host = Host(
        folder=FolderTree().root_folder(),
        host_name=HostName("test_host"),
        attributes=HostAttributes(
            site=SiteId("NO_SITE"),
            alias="test_alias",
            ipaddress=HostAddress(""),
            labels={"cmk/check_mk_server": "yes", "cmk/os_name": "Ubuntu"},
        ),
        cluster_nodes=None,
    )
    host.attributes["test_custom_attr"] = "Custom Attribute"  # type: ignore[typeddict-unknown-key]

    assert _search_text_matches(host, "test_host")  # match host name
    assert _search_text_matches(host, "test_alias")  # match host alias
    assert _search_text_matches(host, "ip-v4-only")  # match tag group
    assert _search_text_matches(host, "Ubuntu")  # match host label
    assert _search_text_matches(host, "Custom Attribute")  # match custom attribute
    assert _search_text_matches(host, "NO_SITE")  # match site id
