#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from contextlib import AbstractContextManager as ContextManager
from contextlib import nullcontext as does_not_raise

import pytest

from livestatus import SiteConfiguration

from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId

from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.piggyback_hub import _validate_piggyback_hub_config, compute_new_config


def default_site_config() -> SiteConfiguration:
    return SiteConfiguration(
        {
            "id": SiteId("mysite"),
            "alias": "Site mysite",
            "socket": ("local", None),
            "disable_wato": True,
            "disabled": False,
            "insecure": False,
            "url_prefix": "/mysite/",
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "replication": "slave",
            "timeout": 5,
            "user_login": True,
            "proxy": None,
            "user_sync": "all",
            "status_host": None,
            "message_broker_port": 5672,
        }
    )


def test_update_sites_with_hub_config() -> None:
    global_settings = {"piggyback_hub_enabled": True}
    configured_sites = {
        SiteId("site1"): default_site_config() | {"globals": {"piggyback_hub_enabled": True}},
        SiteId("site2"): default_site_config() | {"globals": {"piggyback_hub_enabled": False}},
        SiteId("site3"): default_site_config() | {"globals": {}},
    }
    hosts_sites = {
        HostAddress("host1"): SiteId("site1"),
        HostAddress("host2"): SiteId("site2"),
        HostAddress("host3"): SiteId("site3"),
    }

    assert list(compute_new_config(global_settings, configured_sites, hosts_sites)) == [
        ("site1", {HostAddress("host3"): "site3"}),
        ("site3", {HostAddress("host1"): "site1"}),
    ]


@pytest.mark.parametrize(
    ["settings_per_site", "expected_raises"],
    [
        pytest.param(
            {
                "central_site": {"site_piggyback_hub": False},
                "remote_site_1": {"site_piggyback_hub": False},
                "remote_site_2": {"site_piggyback_hub": False},
            },
            does_not_raise(),
            id="all_sites_disabled",
        ),
        pytest.param(
            {
                "central_site": {"site_piggyback_hub": True},
                "remote_site_1": {"site_piggyback_hub": False},
                "remote_site_2": {"site_piggyback_hub": False},
            },
            does_not_raise(),
            id="central_site_enabled",
        ),
        pytest.param(
            {
                "central_site": {"site_piggyback_hub": True},
                "remote_site_1": {"site_piggyback_hub": False},
                "remote_site_2": {"site_piggyback_hub": True},
            },
            does_not_raise(),
            id="central_and_remote_site_enabled",
        ),
        pytest.param(
            {
                "central_site": {"site_piggyback_hub": False},
                "remote_site_1": {"site_piggyback_hub": False},
                "remote_site_2": {"site_piggyback_hub": True},
            },
            pytest.raises(MKUserError),
            id="only_remote_site_enabled",
        ),
    ],
)
def test_validate_piggyback_hub_config(
    settings_per_site: Mapping[SiteId, GlobalSettings],
    expected_raises: ContextManager[pytest.ExceptionInfo[TypeError]],
) -> None:
    with expected_raises:
        _validate_piggyback_hub_config(settings_per_site, SiteId("central_site"))
