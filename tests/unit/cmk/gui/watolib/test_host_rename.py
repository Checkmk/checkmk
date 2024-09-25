#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import shutil
from collections.abc import Iterator

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.utils.redis import disable_redis
from cmk.utils.type_defs import UserId
from cmk.utils.type_defs.host import HostName

from cmk.gui.watolib import check_mk_automations, hosts_and_folders
from cmk.gui.watolib.host_rename import perform_rename_hosts


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

    shutil.rmtree(hosts_and_folders.Folder.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(hosts_and_folders.Folder.root_folder().filesystem_path())


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
    hosts_to_create: list[tuple[HostName, hosts_and_folders.HostAttributes, list[HostName] | None]],
    renamings: list[tuple[HostName, HostName]],
    expected_hosts: set[str],
    expected_clusters: dict[str, set[str]],
) -> None:
    # GIVEN
    if use_subfolder:
        folder = hosts_and_folders.Folder.root_folder().create_subfolder(
            "some_subfolder", "Some Subfolder", {}
        )
    else:
        folder = hosts_and_folders.Folder.root_folder()
    folder.create_hosts(hosts_to_create)

    # WHEN
    perform_rename_hosts(renamings=[(folder, old, new) for old, new in renamings])

    # THEN
    # The folder._hosts is not cleared by the cache invalidation but even if, it
    # would not be invalidated everywhere as not every folder object is in the
    # subfolder hierarchy of the root folder.
    #
    # This also caused the bug in the first place: The cluster renaming
    # created its hosts/folders from Hosts.all() which was not affected by
    # the cache invalidation of _rename_host_in_folder as expected.
    folder._hosts = None  # pylint: disable=protected-access
    hosts = folder.hosts()
    assert set(hosts) == expected_hosts
    for cluster, expected_nodes in expected_clusters.items():
        nodes = hosts[HostName(cluster)].cluster_nodes()
        assert nodes is not None
        assert set(nodes) == expected_nodes
