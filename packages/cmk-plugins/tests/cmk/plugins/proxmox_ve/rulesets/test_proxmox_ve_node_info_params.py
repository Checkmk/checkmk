#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_info import Params
from cmk.plugins.proxmox_ve.rulesets.proxmox_ve_node_info_params import (
    _migrate_required_status,
    _migrate_ruleset,
    NODE_STATUS_DEFAULT,
    SUBSCRIPTION_STATUS_DEFAULT,
)


@pytest.mark.parametrize(
    "old_params,new_node_status,new_subscription_status",
    [
        pytest.param(
            {
                "required_node_status": "online",
                "required_subscription_status": "Active",
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            {
                "online": 0,
                "offline": 1,
                "unknown": 1,
            },
            {
                "new": 1,
                "active": 0,
                "notfound": 1,
                "invalid": 1,
                "expired": 2,
                "suspended": 1,
            },
            id="Node: offline -> OK, Subscription: active -> OK. Every other state will be WARN",
        ),
        pytest.param(
            {
                "required_node_status": None,
                "required_subscription_status": None,
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            {},
            {},
            id="No required statuses -> empty dicts",
        ),
        pytest.param(
            {
                "required_node_status": "32",
                "required_subscription_status": None,
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            NODE_STATUS_DEFAULT,
            {},
            id="Node: invalid string -> default, Subscription: None -> empty dict",
        ),
        pytest.param(
            _migrate_required_status(
                {
                    "required_node_status": "32",
                    "required_subscription_status": None,
                    "subscription_expiration_days_levels": ("fixed", (30, 7)),
                },
                NODE_STATUS_DEFAULT,
            ),
            NODE_STATUS_DEFAULT,
            {},
            id="Do not change already migrated values",
        ),
    ],
)
def test_migrate_required_status(
    old_params: Mapping[str, object],
    new_node_status: Mapping[str, int],
    new_subscription_status: Mapping[str, int],
) -> None:
    assert (
        _migrate_required_status(old_params["required_node_status"], NODE_STATUS_DEFAULT)
        == new_node_status
    )
    assert (
        _migrate_required_status(
            old_params["required_subscription_status"], SUBSCRIPTION_STATUS_DEFAULT
        )
        == new_subscription_status
    )


@pytest.mark.parametrize(
    "old_params,new_params",
    [
        pytest.param(
            {
                "required_node_status": None,
                "required_subscription_status": None,
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            {"subscription_expiration_days_levels": ("fixed", (30, 7))},
            id="No required statuses -> removed from dict",
        ),
        pytest.param(
            {
                "required_node_status": NODE_STATUS_DEFAULT,
                "required_subscription_status": SUBSCRIPTION_STATUS_DEFAULT,
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            {
                "required_node_status": NODE_STATUS_DEFAULT,
                "required_subscription_status": SUBSCRIPTION_STATUS_DEFAULT,
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            id="Everything set -> no change",
        ),
    ],
)
def test_migrate_ruleset(
    old_params: Mapping[str, object],
    new_params: Params,
) -> None:
    assert _migrate_ruleset(old_params) == new_params
