#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.config_sync import (
    replication_path_registry,
    ReplicationPath,
    ReplicationPathType,
)


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_replication_paths() -> None:
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
            ident="host_relations",
            site_path="etc/check_mk/conf.d/relations.mk",
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
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="maps",
            site_path="etc/check_mk/maps.d/wato",
        ),
    ]

    assert dict(replication_path_registry.items()) == {p.ident: p for p in expected}
