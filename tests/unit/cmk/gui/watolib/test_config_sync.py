#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.gui.watolib.config_sync as config_sync


@pytest.mark.parametrize("master, slave, result", [
    pytest.param({"first": {
        "customer": "tribe"
    }}, {
        "first": {
            "customer": "tribe"
        },
        "second": {
            "customer": "tribe"
        }
    }, {"first": {
        "customer": "tribe"
    }},
                 id="Delete user from master"),
    pytest.param(
        {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        }, {}, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        },
        id="New users"),
    pytest.param(
        {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "all admins"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": []
            }
        }, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "adminevery"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": [{
                    "description": "Host on fire"
                }]
            }
        }, {
            "cmkadmin": {
                "customer": None,
                "notification_rules": [{
                    "description": "all admins"
                }]
            },
            "first": {
                "customer": "tribe",
                "notification_rules": [{
                    "description": "Host on fire"
                }]
            }
        },
        id="Update Global user notifications. Retain Customer user notifications"),
])
def test_update_contacts_dict(master, slave, result):
    assert config_sync._update_contacts_dict(master, slave) == result
