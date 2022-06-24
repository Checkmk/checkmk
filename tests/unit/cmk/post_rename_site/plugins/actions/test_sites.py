#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from livestatus import SiteId

import cmk.utils.paths

from cmk.gui.watolib.sites import SiteManagementFactory

from cmk.post_rename_site.plugins.actions.sites import update_site_config


def _write_site_config(config: dict) -> None:
    sites_mk = Path(cmk.utils.paths.default_config_dir, "multisite.d/sites.mk")
    sites_mk.parent.mkdir(parents=True, exist_ok=True)
    with sites_mk.open("w") as f:
        f.write(f"sites.update({config!r})")


def test_update_basic_site_config() -> None:
    _write_site_config(
        {
            "heute": {
                "alias": "Die central Site",
                "disable_wato": True,
                "disabled": False,
                "insecure": False,
                "multisiteurl": "",
                "persist": False,
                "replicate_ec": False,
                "replication": None,
                "timeout": 10,
                "user_login": True,
                "url_prefix": "/heute/",
                "proxy": None,
                "socket": ("local", None),
            },
        }
    )

    update_site_config(SiteId("heute"), SiteId("haha"))

    site_mgmt = SiteManagementFactory().factory()
    all_sites = site_mgmt.load_sites()

    # Site entry has been renamed
    assert "heute" not in all_sites
    assert "haha" in all_sites

    # url_prefix is updated
    assert all_sites[SiteId("haha")]["url_prefix"] == "/haha/"


def test_update_remote_site_status_host_config() -> None:
    _write_site_config(
        {
            "stable": {
                "alias": "Die central Site",
                "socket": ("local", None),
                "proxy": None,
                "timeout": 10,
                "persist": False,
                "url_prefix": "/stable/",
                "status_host": None,
                "disabled": False,
                "replication": None,
                "multisiteurl": "",
                "disable_wato": True,
                "insecure": False,
                "user_login": True,
                "user_sync": "all",
                "replicate_ec": False,
                "replicate_mkps": False,
            },
            "remote": {
                "alias": "Die remote Site 1",
                "socket": (
                    "tcp",
                    {"address": ("127.0.0.1", 6810), "tls": ("encrypted", {"verify": True})},
                ),
                "proxy": {"params": None},
                "timeout": 2,
                "persist": False,
                "url_prefix": "/remote/",
                "status_host": ("stable", "af"),
                "disabled": False,
                "replication": "slave",
                "multisiteurl": "http://localhost/remote/check_mk/",
                "disable_wato": True,
                "insecure": False,
                "user_login": True,
                "user_sync": None,
                "replicate_ec": True,
                "replicate_mkps": False,
                "secret": "watosecret",
            },
        }
    )

    update_site_config(SiteId("stable"), SiteId("dingdong"))

    site_mgmt = SiteManagementFactory().factory()
    all_sites = site_mgmt.load_sites()

    # Site entry has been renamed
    assert "stable" not in all_sites
    assert "dingdong" in all_sites

    # URLs have been updated
    assert all_sites[SiteId("dingdong")]["url_prefix"] == "/dingdong/"

    # Remote site URLs have not been modified
    # Remote site status host was updated
    assert all_sites[SiteId("remote")]["url_prefix"] == "/remote/"
    assert all_sites[SiteId("remote")]["multisiteurl"] == "http://localhost/remote/check_mk/"
    assert all_sites[SiteId("remote")]["status_host"] == ("dingdong", "af")
