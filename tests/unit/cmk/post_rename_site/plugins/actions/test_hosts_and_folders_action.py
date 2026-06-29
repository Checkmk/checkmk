#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from collections.abc import Sequence
from logging import getLogger
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.gui.watolib.hosts_and_folders
import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.watolib.builtin_attributes import HostAttributeSite
from cmk.gui.watolib.host_attributes import (
    HostAttributes,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.post_rename_site.logger import logger
from cmk.post_rename_site.plugins.actions.hosts_and_folders import (
    _update_locked_by,
    update_hosts_and_folders,
)
from cmk.utils.global_ident_type import (
    GlobalIdent,
)
from cmk.utils.tags import TagGroupID

CreateHost = tuple[HostName, HostAttributes, Sequence[HostName] | None]


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


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


@pytest.mark.parametrize(
    "old_site_id, new_site_id, locked_by, expected",
    [
        (SiteId("SITE"), SiteId("NEWSITE"), None, None),
        (
            SiteId("SITE"),
            SiteId("NEWSITE"),
            GlobalIdent(site_id="BAD-SITE-NAME", program_id="aaa", instance_id="bbb"),
            None,
        ),
        (
            SiteId("SITE"),
            SiteId("NEWSITE"),
            GlobalIdent(site_id="SITE", program_id="aaa", instance_id="bbb"),
            ("NEWSITE", "aaa", "bbb"),
        ),
    ],
)
def test_updating_locked_by(
    old_site_id: SiteId,
    new_site_id: SiteId,
    locked_by: GlobalIdent | None,
    expected: Sequence[str],
) -> None:
    updated_locked_by: Sequence[str] | None = _update_locked_by(old_site_id, new_site_id, locked_by)
    assert updated_locked_by == expected


def test_updating_site_name_for_dcd(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    We have one site and two hosts.
        * host-2 is locked by host-1

    Updating the site name for host-1 should update host-2 and the host-2.locked_by
    """

    def extend_site_context(m: pytest.MonkeyPatch) -> None:
        m.setattr(
            active_config,
            "sites",
            SiteConfigurations(
                {
                    **active_config.sites,
                    SiteId("NEWSITE"): SiteConfiguration(
                        id=SiteId("NEWSITE"),
                        alias="No Site",
                        socket=("local", None),
                        disable_wato=True,
                        disabled=False,
                        insecure=False,
                        url_prefix="/NEWSITE/",
                        multisiteurl="",
                        persist=False,
                        replicate_ec=False,
                        replicate_mkps=False,
                        replication=None,
                        timeout=5,
                        user_login=True,
                        proxy=None,
                        user_attribute_sync_connections="all",
                        status_host=None,
                        message_broker_port=5672,
                        is_trusted=False,
                    ),
                }
            ),
        )

    old_site_id = SiteId("NO_SITE")
    new_site_id = SiteId("NEWSITE")

    host_info_1: CreateHost = (HostName("host-1"), {"site": old_site_id}, [])
    host_info_2: CreateHost = (
        HostName("host-2"),
        {
            "site": old_site_id,
            "locked_by": (old_site_id, "aaa", "bbb"),
        },
        [],
    )

    ## Let's prepare the initial state of the hosts.
    root = folder_tree().root_folder()
    root.create_hosts(
        [host_info_1, host_info_2],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=user,
    )

    ## Check the initial state of the hosts.
    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == old_site_id
    assert host_2.attributes.get("site") == old_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() == GlobalIdent(
        site_id=old_site_id, program_id="aaa", instance_id="bbb"
    )

    ## Update the site name.
    with monkeypatch.context() as m:
        extend_site_context(m)
        update_hosts_and_folders(
            old_site_id=old_site_id, new_site_id=new_site_id, logger=getLogger("test")
        )

    ## Check the state of the hosts after the update.
    root = folder_tree().root_folder()

    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == new_site_id
    assert host_2.attributes.get("site") == new_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() == GlobalIdent(
        site_id=new_site_id, program_id="aaa", instance_id="bbb"
    )
    ## Let's change the site back.
    update_hosts_and_folders(
        old_site_id=new_site_id, new_site_id=old_site_id, logger=getLogger("test")
    )

    ## Check the state of the hosts, it should be exactly the same as the initial one.
    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == old_site_id
    assert host_2.attributes.get("site") == old_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() == GlobalIdent(
        site_id=old_site_id, program_id="aaa", instance_id="bbb"
    )


def test_updating_site_name_without_dcd(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    We have two site and two separate hosts.

    Updating the site name for host-1 shouldn't change host-2.
    """

    def extend_site_context(m: pytest.MonkeyPatch) -> None:
        m.setattr(
            active_config,
            "sites",
            SiteConfigurations(
                {
                    **active_config.sites,
                    SiteId("HOST2SITE"): SiteConfiguration(
                        id=SiteId("HOST2SITE"),
                        alias="No Site",
                        socket=("local", None),
                        disable_wato=True,
                        disabled=False,
                        insecure=False,
                        url_prefix="/HOST2SITE/",
                        multisiteurl="",
                        persist=False,
                        replicate_ec=False,
                        replicate_mkps=False,
                        replication=None,
                        timeout=5,
                        user_login=True,
                        proxy=None,
                        user_attribute_sync_connections="all",
                        status_host=None,
                        message_broker_port=5672,
                        is_trusted=False,
                    ),
                }
            ),
        )

    old_site_id = SiteId("NO_SITE")
    new_site_id = SiteId("NEWSITE")
    host_2_site_id = SiteId("HOST2SITE")

    host_info_1: CreateHost = (HostName("host-1"), {"site": old_site_id}, [])
    host_info_2: CreateHost = (
        HostName("host-2"),
        {
            "site": host_2_site_id,
        },
        [],
    )

    ## Let's prepare the initial state of the hosts.
    root = folder_tree().root_folder()
    with monkeypatch.context() as m:
        extend_site_context(m)
        root.create_hosts(
            [host_info_1, host_info_2],
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=user,
        )

    ## Check the initial state of the hosts.
    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == old_site_id
    assert host_2.attributes.get("site") == host_2_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() is None

    ## Update the site name.
    update_hosts_and_folders(
        old_site_id=old_site_id, new_site_id=new_site_id, logger=getLogger("test")
    )

    ## Check the state of the hosts after the update.
    root = folder_tree().root_folder()

    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == new_site_id
    assert host_2.attributes.get("site") == host_2_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() is None

    ## Let's change the site back.
    update_hosts_and_folders(
        old_site_id=new_site_id, new_site_id=old_site_id, logger=getLogger("test")
    )

    ## Check the state of the hosts, it should be exactly the same as the initial one.
    host_1 = root.load_host(HostName("host-1"))
    host_2 = root.load_host(HostName("host-2"))

    assert host_1.attributes.get("site") == old_site_id
    assert host_2.attributes.get("site") == host_2_site_id

    assert host_1.locked_by() is None
    assert host_2.locked_by() is None
