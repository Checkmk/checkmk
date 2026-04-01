#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.site_config import sites_ready_for_remote_automation


def _site_config(*, replication: bool, secret: bool) -> SiteConfiguration:
    site_config = SiteConfiguration(
        alias="Remote",
        disable_wato=False,
        disabled=False,
        id=SiteId("remote"),
        insecure=False,
        is_trusted=False,
        message_broker_port=5672,
        multisiteurl="",
        persist=False,
        proxy=None,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave" if replication else None,
        socket=("local", None),
        status_host=None,
        timeout=5,
        url_prefix="/remote/",
        user_login=True,
        user_sync="all",
    )
    if secret:
        site_config["secret"] = "s3cr3t"
    return site_config


def test_sites_ready_for_remote_automation_empty() -> None:
    """No sites configured means nothing to sync."""
    assert sites_ready_for_remote_automation(SiteConfigurations({})) == {}


def test_sites_ready_for_remote_automation_no_replication() -> None:
    """Site without replication enabled is not a remote site and must be excluded."""
    sites = SiteConfigurations({SiteId("r"): _site_config(replication=False, secret=True)})
    assert sites_ready_for_remote_automation(sites) == {}


def test_sites_ready_for_remote_automation_no_secret() -> None:
    """Site in removal (replication enabled, no login secret) must be excluded."""
    sites = SiteConfigurations({SiteId("r"): _site_config(replication=True, secret=False)})
    assert sites_ready_for_remote_automation(sites) == {}


def test_sites_ready_for_remote_automation_ready() -> None:
    """Site with replication enabled and a secret is included as-is."""
    site_id = SiteId("r")
    site_cfg = _site_config(replication=True, secret=True)
    sites = SiteConfigurations({site_id: site_cfg})
    assert sites_ready_for_remote_automation(sites) == {site_id: site_cfg}


def test_sites_ready_for_remote_automation_mixed() -> None:
    """Only sites with both replication and secret are returned."""
    ready_id = SiteId("ready")
    no_secret_id = SiteId("no_secret")
    no_replication_id = SiteId("no_replication")
    ready_cfg = _site_config(replication=True, secret=True)
    sites = SiteConfigurations(
        {
            ready_id: ready_cfg,
            no_secret_id: _site_config(replication=True, secret=False),
            no_replication_id: _site_config(replication=False, secret=True),
        }
    )
    result = sites_ready_for_remote_automation(sites)
    assert result == {ready_id: ready_cfg}
