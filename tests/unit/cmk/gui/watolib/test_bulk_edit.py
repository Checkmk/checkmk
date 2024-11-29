# Copyright (C) 2024Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from cmk.gui.plugins.wato.utils import _search_text_matches
from cmk.gui.watolib.hosts_and_folders import Folder, Host
from livestatus import SiteId


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_search_text_matches() -> None:
    host = Host(
        folder=Folder.root_folder(),
        host_name="test_host",
        attributes={
            "site": SiteId("test_site_id"),
            "alias": "test_alias",
            "ipaddress": "",
            "labels": {"cmk/check_mk_server": "yes", "cmk/os_name": "Ubuntu"},
        },
        cluster_nodes=None,
    )
    host._attributes["test_custom_attr"] = "Custom Attribute"  # type: ignore[typeddict-unknown-key]

    assert _search_text_matches(host, "test_host")  # match host name
    assert _search_text_matches(host, "test_alias")  # match host alias
    assert _search_text_matches(host, "ip-v4-only")  # match tag group
    assert _search_text_matches(host, "Ubuntu")  # match host label
    assert _search_text_matches(host, "Custom Attribute")  # match custom attribute
    assert _search_text_matches(host, "test_site_id")  # match site id
