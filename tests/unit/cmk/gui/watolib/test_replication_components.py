#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.watolib.activate_changes import get_replication_components
from cmk.gui.watolib.config_sync import ReplicationPath, ReplicationPathType
from cmk.livestatus_client import SiteConfiguration

_REPLICATION_PATHS = [
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="check_mk", site_path="etc/a"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="mkeventd", site_path="etc/b"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="mkeventd_mkp", site_path="etc/c"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="local", site_path="local/d"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="mkps", site_path="var/e"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="mkps_avail", site_path="var/f"),
    ReplicationPath.make(ty=ReplicationPathType.DIR, ident="mkps_disabled", site_path="var/g"),
]

_ALL_IDENTS = {
    "check_mk",
    "mkeventd",
    "mkeventd_mkp",
    "local",
    "mkps",
    "mkps_avail",
    "mkps_disabled",
}


def _site_config(*, replicate_ec: bool, replicate_mkps: bool) -> SiteConfiguration:
    return SiteConfiguration(
        id=SiteId("mysite"),
        alias="Site mysite",
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/mysite/",
        multisiteurl="",
        persist=False,
        replicate_ec=replicate_ec,
        replicate_mkps=replicate_mkps,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


@pytest.mark.parametrize(
    "replicate_ec, expected",
    [
        (True, _ALL_IDENTS),
        (False, {"check_mk", "local", "mkps", "mkps_avail", "mkps_disabled"}),
    ],
)
def test_ec_paths_are_replicated_only_if_requested(replicate_ec: bool, expected: set[str]) -> None:
    site_config = _site_config(replicate_ec=replicate_ec, replicate_mkps=True)

    components = get_replication_components(site_config, _REPLICATION_PATHS)

    assert {c.ident for c in components} == expected


@pytest.mark.parametrize(
    "replicate_mkps, expected",
    [
        (True, _ALL_IDENTS),
        (False, {"check_mk", "mkeventd", "mkeventd_mkp"}),
    ],
)
def test_mkp_paths_are_replicated_only_if_requested(
    replicate_mkps: bool, expected: set[str]
) -> None:
    site_config = _site_config(replicate_ec=True, replicate_mkps=replicate_mkps)

    components = get_replication_components(site_config, _REPLICATION_PATHS)

    assert {c.ident for c in components} == expected
