#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import shutil
import threading
from collections.abc import Iterator

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.redis import disable_redis

from cmk.gui.background_job._interface import BackgroundProcessInterface
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib import check_mk_automations
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_rename import perform_rename_hosts
from cmk.gui.watolib.hosts_and_folders import folder_tree


@pytest.fixture(autouse=True)
def test_env(
    monkeypatch: MonkeyPatch, with_admin_login: UserId, load_config: None
) -> Iterator[None]:
    monkeypatch.setattr(
        check_mk_automations,
        "check_mk_local_automation_serialized",
        lambda **_: ("", "[{}]"),
    )

    with disable_redis():
        yield

    shutil.rmtree(folder_tree().root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(folder_tree().root_folder().filesystem_path())


@pytest.mark.parametrize(
    "hosts_to_create,renamings,expected_hosts,expected_clusters",
    [
        pytest.param(
            [
                (HostName("host1"), {}, None),
                (HostName("host2"), {}, None),
            ],
            [
                (HostName("host1"), HostName("new_host1")),
                (HostName("host2"), HostName("new_host2")),
            ],
            {"new_host1", "new_host2"},
            {},
            id="rename two hosts",
        ),
        pytest.param(
            [
                (HostName("host1"), {}, None),
                (HostName("host2"), {}, None),
                (HostName("cluster_host"), {}, [HostName("host1"), HostName("host2")]),
            ],
            [(HostName("host1"), HostName("new_host1"))],
            {"new_host1", "host2", "cluster_host"},
            {"cluster_host": {"new_host1", "host2"}},
            id="rename one host in cluster",
        ),
        pytest.param(
            [
                (HostName("host1"), {}, None),
                (HostName("host2"), {}, None),
                (HostName("cluster_host"), {}, [HostName("host1"), HostName("host2")]),
            ],
            [
                (HostName("host1"), HostName("new_host1")),
                (HostName("cluster_host"), HostName("new_cluster_host")),
            ],
            {"new_host1", "host2", "new_cluster_host"},
            {"new_cluster_host": {"new_host1", "host2"}},
            id="rename host then rename cluster",
        ),
        pytest.param(
            [
                (HostName("host1"), {}, None),
                (HostName("host2"), {}, None),
                (HostName("cluster_host"), {}, [HostName("host1"), HostName("host2")]),
            ],
            [
                (HostName("cluster_host"), HostName("new_cluster_host")),
                (HostName("host1"), HostName("new_host1")),
            ],
            {"new_host1", "host2", "new_cluster_host"},
            {"new_cluster_host": {"new_host1", "host2"}},
            id="rename cluster then rename host",
        ),
    ],
)
@pytest.mark.parametrize("use_subfolder", [True, False])
def test_rename_host(
    use_subfolder: bool,
    hosts_to_create: list[tuple[HostName, HostAttributes, list[HostName] | None]],
    renamings: list[tuple[HostName, HostName]],
    expected_hosts: set[str],
    expected_clusters: dict[str, set[str]],
) -> None:
    # GIVEN
    job_interface = BackgroundProcessInterface(
        "", "", logging.getLogger(), threading.Event(), gui_context, open("/dev/null", "w")
    )
    if use_subfolder:
        folder = (
            folder_tree()
            .root_folder()
            .create_subfolder("some_subfolder", "Some Subfolder", {}, pprint_value=False)
        )
    else:
        folder = folder_tree().root_folder()
    folder.create_hosts(hosts_to_create, pprint_value=False)

    # WHEN
    perform_rename_hosts(
        renamings=[(folder, old, new) for old, new in renamings],
        job_interface=job_interface,
        site_configs={
            SiteId("NO_SITE"): {
                "id": SiteId("NO_SITE"),
                "alias": "Local site NO_SITE",
                "socket": ("local", None),
                "disable_wato": True,
                "disabled": False,
                "insecure": False,
                "url_prefix": "/NO_SITE/",
                "multisiteurl": "",
                "persist": False,
                "replicate_ec": False,
                "replicate_mkps": False,
                "replication": None,
                "timeout": 5,
                "user_login": True,
                "proxy": None,
                "user_sync": "all",
                "status_host": None,
                "message_broker_port": 5672,
            }
        },
        pprint_value=False,
        use_git=False,
        debug=False,
    )

    # THEN
    # The folder._hosts is not cleared by the cache invalidation but even if, it
    # would not be invalidated everywhere as not every folder object is in the
    # subfolder hierarchy of the root folder.
    #
    # This also caused the bug in the first place: The cluster renaming
    # created its hosts/folders from Hosts.all() which was not affected by
    # the cache invalidation of _rename_host_in_folder as expected.
    folder._hosts = None
    hosts = folder.hosts()
    assert set(hosts) == expected_hosts
    for cluster, expected_nodes in expected_clusters.items():
        nodes = hosts[HostName(cluster)].cluster_nodes()
        assert nodes is not None
        assert set(nodes) == expected_nodes
