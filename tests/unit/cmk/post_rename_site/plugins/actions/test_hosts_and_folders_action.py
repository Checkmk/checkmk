#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

from pytest import MonkeyPatch

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils.paths
from cmk.utils.tags import TagGroupID

import cmk.gui.watolib.hosts_and_folders
from cmk.gui.watolib.builtin_attributes import HostAttributeSite
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.post_rename_site.logger import logger
from cmk.post_rename_site.plugins.actions.hosts_and_folders import update_hosts_and_folders


def _write_folder_attributes(folder_attributes: dict) -> Path:
    dot_wato = cmk.utils.paths.default_config_dir / "conf.d/wato/.wato"
    dot_wato.parent.mkdir(parents=True, exist_ok=True)
    with dot_wato.open("w") as f:
        f.write(repr(folder_attributes))
    return dot_wato


def _write_hosts_mk(content: str) -> Path:
    path = cmk.utils.paths.default_config_dir / "conf.d/wato/hosts.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(content)
    return path


def test_rewrite_folder_explicit_site() -> None:
    _write_folder_attributes(
        {
            "title": "Main",
            "attributes": {
                "site": "stable",
                "meta_data": {
                    "created_at": 1627991988.6232662,
                    "updated_at": 1627991994.7575116,
                    "created_by": None,
                },
            },
            "num_hosts": 0,
            "lock": False,
            "lock_subfolders": False,
            "__id": "9f5a85386b7c4ad68738d66a49a4bfa9",
        }
    )

    folder = folder_tree().root_folder()
    assert folder.attributes.get("site") == "stable"

    update_hosts_and_folders(SiteId("stable"), SiteId("dingdong"), logger)
    assert folder.attributes.get("site") == "dingdong"


def test_rewrite_host_explicit_site() -> None:
    _write_hosts_mk(
        """# Created by WATO
# encoding: utf-8

all_hosts += ['ag']

host_tags.update({'ag': {'site': 'stable', 'address_family': 'ip-v4-only', 'ip-v4': 'ip-v4', 'agent': 'cmk-agent', 'tcp': 'tcp', 'piggyback': 'auto-piggyback', 'snmp_ds': 'no-snmp', 'criticality': 'prod', 'networking': 'lan'}})

host_labels.update({})

# Explicit IPv4 addresses
ipaddresses.update({'ag': '127.0.0.1'})

# Host attributes (needed for WATO)
host_attributes.update(
{'ag': {'ipaddress': '127.0.0.1', 'site': 'stable', 'meta_data': {'created_at': 1627486290.0, 'created_by': 'cmkadmin', 'updated_at': 1627993165.0079741}}})
"""
    )

    assert folder_tree().root_folder().load_host(HostName("ag")).attributes.get("site") == "stable"
    update_hosts_and_folders(SiteId("stable"), SiteId("dingdong"), logger)
    assert (
        folder_tree().root_folder().load_host(HostName("ag")).attributes.get("site") == "dingdong"
    )

    # also verify that the attributes (host_tags) not read by WATO have been updated
    hosts_config = folder_tree().root_folder()._load_hosts_file()
    assert hosts_config is not None
    assert hosts_config["host_tags"]["ag"]["site"] == "dingdong"


def test_rewrite_tags_no_explicit_site_set(monkeypatch: MonkeyPatch) -> None:
    _write_folder_attributes(
        {
            "title": "Main",
            "attributes": {
                "meta_data": {
                    "created_at": 1627991988.6232662,
                    "updated_at": 1627991994.7575116,
                    "created_by": None,
                }
            },
            "num_hosts": 0,
            "lock": False,
            "lock_subfolders": False,
            "__id": "9f5a85386b7c4ad68738d66a49a4bfa9",
        }
    )

    _write_hosts_mk(
        """# Created by WATO
# encoding: utf-8

all_hosts += ['ag']

host_tags.update({'ag': {'site': 'NO_SITE', 'address_family': 'ip-v4-only', 'ip-v4': 'ip-v4', 'agent': 'cmk-agent', 'tcp': 'tcp', 'piggyback': 'auto-piggyback', 'snmp_ds': 'no-snmp', 'criticality': 'prod', 'networking': 'lan'}})

host_labels.update({})

# Explicit IPv4 addresses
ipaddresses.update({'ag': '127.0.0.1'})

# Host attributes (needed for WATO)
host_attributes.update(
{'ag': {'ipaddress': '127.0.0.1', 'meta_data': {'created_at': 1627486290.0, 'created_by': 'cmkadmin', 'updated_at': 1627993165.0079741}}})
"""
    )

    tree = folder_tree()
    root_folder = tree.root_folder()

    assert root_folder.attributes.get("site") is None
    assert root_folder.load_host(HostName("ag")).attributes.get("site") is None
    assert root_folder.load_host(HostName("ag")).site_id() == "NO_SITE"

    # Simulate changed omd_site that we would have in application code in the moment the rename
    # action is executed.
    monkeypatch.setattr(cmk.gui.watolib.hosts_and_folders, "omd_site", lambda: "dingdong")
    monkeypatch.setattr(HostAttributeSite, "default_value", lambda self: "dingdong")

    update_hosts_and_folders(SiteId("NO_SITE"), SiteId("dingdong"), logger)

    tree.invalidate_caches()

    assert root_folder.attributes.get("site") is None
    assert root_folder.load_host(HostName("ag")).attributes.get("site") is None
    assert root_folder.load_host(HostName("ag")).site_id() == "dingdong"
    assert root_folder.load_host(HostName("ag")).tag_groups()[TagGroupID("site")] == "dingdong"

    # also verify that the attributes (host_tags) not read by WATO have been updated
    hosts_config = root_folder._load_hosts_file()
    assert hosts_config is not None
    assert hosts_config["host_tags"]["ag"]["site"] == "dingdong"
