#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator

import pytest

from livestatus import SiteConfiguration

import cmk.ccc.version as cmk_version
from cmk.ccc.site import SiteId
from cmk.gui.watolib import activate_changes
from cmk.gui.watolib.config_sync import (
    replication_path_registry,
    ReplicationPath,
    ReplicationPathType,
)
from tests.testlib.common.utils import reset_registries

EDITION = cmk_version.Edition.COMMUNITY


@pytest.fixture(autouse=True)
def restore_orig_replication_paths() -> Generator[None]:
    with reset_registries([replication_path_registry]):
        yield


def _expected_replication_paths() -> list[ReplicationPath]:
    expected = [
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="check_mk",
            site_path="etc/check_mk/conf.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="multisite",
            site_path="etc/check_mk/multisite.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="htpasswd",
            site_path="etc/htpasswd",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="password_store.secret",
            site_path="etc/password_store.secret",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="auth.serials",
            site_path="etc/auth.serials",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="stored_passwords",
            site_path="var/check_mk/stored_passwords",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="product_usage_analytics",
            site_path="etc/check_mk/product_usage_analytics.mk",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="usersettings",
            site_path="var/check_mk/web",
            excludes_exact_match=["last_login.mk", "report-thumbnails", "session_info.mk"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps",
            site_path="var/check_mk/packages",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps_avail",
            site_path="var/check_mk/packages_local",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps_disabled",
            site_path="var/check_mk/disabled_packages",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="local",
            site_path="local",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="distributed_wato",
            site_path="etc/check_mk/conf.d/distributed_wato.mk",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="omd",
            site_path="etc/omd",
            excludes_exact_match=["site.conf", "instance_id"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="rabbitmq",
            site_path="etc/rabbitmq/definitions.d",
            excludes_exact_match=["00-default.json", "definitions.json"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="frozen_aggregations",
            site_path="var/check_mk/frozen_aggregations",
            excludes_exact_match=[],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="topology",
            site_path="var/check_mk/topology/configs",
            excludes_exact_match=[],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="topology_settings",
            site_path="var/check_mk/topology/topology_settings",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="apache_proccess_tuning",
            site_path="etc/check_mk/apache.d/wato",
            excludes_exact_match=[],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd",
            site_path="etc/check_mk/mkeventd.d/wato",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkeventd_mkp",
            site_path="etc/check_mk/mkeventd.d/mkp/rule_packs",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="diskspace",
            site_path="etc/check_mk/diskspace.d/wato",
        ),
    ]

    return expected


def _default_site_config() -> SiteConfiguration:
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
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_sync="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )


def test_get_replication_paths_defaults(request_context: None) -> None:
    expected = _expected_replication_paths()
    assert sorted(
        replication_path_registry.values(),
        key=lambda replication_path: replication_path.ident,
    ) == sorted(
        expected,
        key=lambda replication_path: replication_path.ident,
    )


@pytest.mark.parametrize("replicate_ec", [None, True, False])
@pytest.mark.parametrize("replicate_mkps", [None, True, False])
def test_get_replication_components(
    monkeypatch: pytest.MonkeyPatch,
    replicate_ec: bool | None,
    replicate_mkps: bool | None,
    request_context: None,
) -> None:
    site_config = _default_site_config()

    if replicate_ec is not None:
        site_config["replicate_ec"] = replicate_ec
    if replicate_mkps is not None:
        site_config["replicate_mkps"] = replicate_mkps

    expected = _expected_replication_paths()

    if not replicate_ec:
        expected = [e for e in expected if e.ident not in ["mkeventd", "mkeventd_mkp"]]

    if not replicate_mkps:
        expected = [
            e for e in expected if e.ident not in ["local", "mkps", "mkps_avail", "mkps_disabled"]
        ]

    assert sorted(
        activate_changes._get_replication_components(site_config),
        key=lambda replication_path: replication_path.ident,
    ) == sorted(
        expected,
        key=lambda replication_path: replication_path.ident,
    )
