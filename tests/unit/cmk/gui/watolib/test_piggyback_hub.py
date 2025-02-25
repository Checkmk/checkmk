#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from livestatus import SiteConfiguration, SiteId

from cmk.utils.hostaddress import HostAddress

from cmk.gui.watolib.piggyback_hub import compute_new_config

from cmk.piggyback.hub import PiggybackHubConfig


def test_update_sites_with_hub_config() -> None:
    global_settings = {"piggyback_hub_enabled": True}
    configured_sites = {
        SiteId("site1"): SiteConfiguration(globals={"piggyback_hub_enabled": True}),
        SiteId("site2"): SiteConfiguration(globals={"piggyback_hub_enabled": False}),
        SiteId("site3"): SiteConfiguration(globals={}),
    }
    hosts_sites = {
        HostAddress("host1"): SiteId("site1"),
        HostAddress("host2"): SiteId("site2"),
        HostAddress("host3"): SiteId("site3"),
    }

    assert compute_new_config(global_settings, configured_sites, hosts_sites) == {
        SiteId("site1"): PiggybackHubConfig(targets={HostAddress("host3"): SiteId("site3")}),
        SiteId("site3"): PiggybackHubConfig(targets={HostAddress("host1"): SiteId("site1")}),
    }
