#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Any

import cmk.utils.version as cmk_version
import cmk.gui.views

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.views.icons  # pylint: disable=no-name-in-module

import cmk.gui.plugins.views.icons as icons


def test_builtin_icons_and_actions():
    expected_icons_and_actions = [
        'action_menu',
        'aggregation_checks',
        'aggregations',
        'check_manpage',
        'check_period',
        'crashed_check',
        'custom_action',
        'download_agent_output',
        'download_snmp_walk',
        'icon_image',
        'inventory',
        'logwatch',
        'mkeventd',
        'notes',
        'parent_child_topology',
        'perfgraph',
        'prediction',
        'reschedule',
        'rule_editor',
        'stars',
        'status_acknowledged',
        'status_active_checks',
        'status_comments',
        'status_downtimes',
        'status_flapping',
        'status_notification_period',
        'status_notifications_enabled',
        'status_passive_checks',
        'status_service_period',
        'status_stale',
        'wato',
    ]

    if not cmk_version.is_raw_edition():
        expected_icons_and_actions += [
            'agent_deployment',
            'deployment_status',
            'status_shadow',
            'ntop_host',
            'ntop_service_interface',
        ]

    cmk.gui.views.transform_old_dict_based_icons()
    builtin_icons = sorted(icons.get_multisite_icons().keys())
    assert builtin_icons == sorted(expected_icons_and_actions)


def test_legacy_icon_plugin():
    icon: Dict[str, Any] = {
        "columns": ["column"],
        "host_columns": ["hcol"],
        "service_columns": ["scol"],
        "paint": lambda: "bla",
        "sort_index": 10,
        "toplevel": True,
    }
    cmk.gui.views.multisite_icons_and_actions["legacy"] = icon
    cmk.gui.views.transform_old_dict_based_icons()

    registered_icon = icons.get_multisite_icons()["legacy"]
    assert registered_icon.columns() == icon["columns"]
    assert registered_icon.host_columns() == icon["host_columns"]
    assert registered_icon.service_columns() == icon["service_columns"]
    assert registered_icon.render() == icon["paint"]()
    assert registered_icon.toplevel() is True
    assert registered_icon.sort_index() == 10


def test_legacy_icon_plugin_defaults():
    icon = {
        "columns": ["column"],
        "host_columns": ["hcol"],
        "service_columns": ["scol"],
        "paint": lambda: "bla",
    }
    cmk.gui.views.multisite_icons_and_actions["legacy"] = icon
    cmk.gui.views.transform_old_dict_based_icons()

    registered_icon = icons.get_multisite_icons()["legacy"]
    assert registered_icon.toplevel() is False
    assert registered_icon.sort_index() == 30
