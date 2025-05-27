#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

import pytest

from livestatus import (
    NetworkSocketDetails,
    ProxyConfig,
    SiteConfiguration,
    SiteConfigurations,
    TLSParams,
)

from cmk.ccc.site import SiteId

from cmk.gui.watolib.sites import site_management_registry

from cmk.post_rename_site.logger import logger
from cmk.post_rename_site.plugins.actions.sites import update_site_config


@pytest.fixture(name="site_config_file")
def fixture_site_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterable[Path]:
    monkeypatch.setattr("cmk.utils.paths.default_config_dir", tmp_path)
    sites_mk = tmp_path / "multisite.d" / "sites.mk"
    sites_mk.parent.mkdir(parents=True)
    yield sites_mk


def _write_site_config(sites_mk: Path, config: SiteConfigurations) -> None:
    with sites_mk.open("w") as f:
        f.write(f"sites.update({config!r})")


def test_update_basic_site_config(site_config_file: Path) -> None:
    _write_site_config(
        site_config_file,
        SiteConfigurations(
            {
                SiteId("heute"): SiteConfiguration(
                    id=SiteId("heute"),
                    alias="Die central Site",
                    disable_wato=True,
                    disabled=False,
                    insecure=False,
                    multisiteurl="",
                    persist=False,
                    replicate_ec=False,
                    replicate_mkps=False,
                    replication=None,
                    message_broker_port=5672,
                    timeout=10,
                    user_login=True,
                    url_prefix="/heute/",
                    proxy=None,
                    socket=("local", None),
                    status_host=None,
                    user_sync="all",
                ),
            }
        ),
    )

    update_site_config(SiteId("heute"), SiteId("haha"), logger)

    all_sites = site_management_registry["site_management"].load_sites()

    # Site entry has been renamed
    assert "heute" not in all_sites
    assert "haha" in all_sites

    assert all_sites[SiteId("haha")]["id"] == "haha"
    assert all_sites[SiteId("haha")]["url_prefix"] == "/haha/"


def test_update_remote_site_status_host_config(site_config_file: Path) -> None:
    _write_site_config(
        site_config_file,
        SiteConfigurations(
            {
                SiteId("stable"): SiteConfiguration(
                    id=SiteId("stable"),
                    alias="Die central Site",
                    socket=("local", None),
                    proxy=None,
                    timeout=10,
                    persist=False,
                    url_prefix="/stable/",
                    status_host=None,
                    disabled=False,
                    replication=None,
                    message_broker_port=5672,
                    multisiteurl="",
                    disable_wato=True,
                    insecure=False,
                    user_login=True,
                    user_sync="all",
                    replicate_ec=False,
                    replicate_mkps=False,
                ),
                SiteId("remote"): SiteConfiguration(
                    id=SiteId("remote"),
                    alias="Die remote Site 1",
                    socket=(
                        "tcp",
                        NetworkSocketDetails(
                            address=("127.0.0.1", 6810), tls=("encrypted", TLSParams(verify=True))
                        ),
                    ),
                    proxy=ProxyConfig(params=None),
                    timeout=2,
                    persist=False,
                    url_prefix="/remote/",
                    status_host=(SiteId("stable"), "af"),
                    disabled=False,
                    replication="slave",
                    message_broker_port=5672,
                    multisiteurl="http://localhost/remote/check_mk/",
                    disable_wato=True,
                    insecure=False,
                    user_login=True,
                    user_sync=None,
                    replicate_ec=True,
                    replicate_mkps=False,
                    secret="watosecret",
                ),
            }
        ),
    )

    update_site_config(SiteId("stable"), SiteId("dingdong"), logger)

    all_sites = site_management_registry["site_management"].load_sites()

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
