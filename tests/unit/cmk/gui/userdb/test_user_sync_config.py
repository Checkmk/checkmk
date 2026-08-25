#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``user_attribute_sync_connections`` resolution."""

from typing import Literal, TYPE_CHECKING

import pytest

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.userdb._user_sync_config import user_sync_config, UserSyncConfig

if TYPE_CHECKING:
    from tests.testlib.gui.web_test_app import SetConfig


@pytest.mark.parametrize(
    ["per_site_value", "expected"],
    [
        ("disabled", None),
        ("all", "all"),
        (["ldap_a", "ldap_b"], ("list", ["ldap_a", "ldap_b"])),
    ],
)
def test_user_sync_config_per_site_value_wins(
    per_site_value: Literal["all", "disabled"] | list[str],
    expected: UserSyncConfig,
    set_config: SetConfig,
    request_context: None,
) -> None:
    site_id = omd_site()
    sites = {
        **active_config.sites,
        site_id: {
            **active_config.sites[site_id],
            "user_attribute_sync_connections": per_site_value,
        },
    }
    with set_config(sites=sites):
        assert user_sync_config() == expected


@pytest.mark.parametrize(
    ["global_value", "expected"],
    [
        ("disabled", None),
        ("all", "all"),
        (["ldap_a"], ("list", ["ldap_a"])),
    ],
)
def test_user_sync_config_absent_key_falls_through_to_global(
    global_value: Literal["all", "disabled"] | list[str],
    expected: UserSyncConfig,
    set_config: SetConfig,
    request_context: None,
) -> None:
    site_id = omd_site()
    site_config = dict(active_config.sites[site_id])
    site_config.pop("user_attribute_sync_connections", None)
    sites = {**active_config.sites, site_id: site_config}
    with set_config(sites=sites, user_attribute_sync_connections=global_value):
        assert user_sync_config() == expected


@pytest.mark.parametrize(
    ["propagated_global", "expected"],
    [
        ("disabled", None),
        ("all", "all"),
        (["ldap_a"], ("list", ["ldap_a"])),
    ],
)
def test_user_sync_config_on_remote_uses_propagated_global(
    propagated_global: Literal["all", "disabled"] | list[str],
    expected: UserSyncConfig,
    set_config: SetConfig,
    request_context: None,
    remote_site: None,
) -> None:
    """The seeded local self-default ("all") must not shadow the value the
    central site resolved and propagated via ``get_site_globals()``."""
    site_id = omd_site()
    sites = {
        site_id: {
            **active_config.sites[site_id],
            "user_attribute_sync_connections": "all",
        },
    }
    with set_config(sites=sites, user_attribute_sync_connections=propagated_global):
        assert user_sync_config() == expected
