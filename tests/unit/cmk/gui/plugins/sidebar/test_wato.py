#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List
import pytest  # type: ignore[import]

import cmk.utils.version as cmk_version
from cmk.gui.plugins.sidebar.wato import get_wato_menu_items


def expected_items() -> Dict[str, List[str]]:
    agents_items = []

    if cmk_version.is_raw_edition():
        agents_items += [
            'download_agents_linux',
            'download_agents_windows',
        ]
    else:
        agents_items += [
            'agents',
        ]

    agents_items += [
        'download_agents',
        'wato.py?mode=rulesets&group=vm_cloud_container',
        'wato.py?mode=rulesets&group=datasource_programs',
        'wato.py?mode=rulesets&group=custom_integrations',
        'wato.py?mode=rulesets&group=agent',
        'wato.py?mode=rulesets&group=snmp',
    ]

    events_items = [
        'notifications',
        'mkeventd_rule_packs',
    ]

    if not cmk_version.is_raw_edition():
        events_items.append('alert_handlers')

    maintenance_items = ['backup']

    if not cmk_version.is_raw_edition():
        maintenance_items.append('license_usage')
        maintenance_items.append('mkps')

    maintenance_items += [
        'diagnostics',
        'analyze_config',
        'background_jobs_overview',
        'version.py',
    ]

    hosts_items = [
        'folder',
        'wato.py?mode=rulesets&group=host_monconf',
        'tags',
    ]

    if not cmk_version.is_raw_edition():
        hosts_items.append('dcd_connections')

    hosts_items += [
        'host_groups',
        'host_attrs',
        'wato.py?mode=rulesets&group=inventory',
    ]

    users_items = [
        'users',
        'contact_groups',
        'roles',
        'ldap_config',
        'user_attrs',
    ]

    if cmk_version.is_managed_edition():
        users_items.insert(0, 'customer_management')

    return {
        'agents': agents_items,
        'events': events_items,
        'general': [
            'rule_search',
            'globalvars',
            'read_only',
            'predefined_conditions',
            'timeperiods',
            'passwords',
            'sites',
            'auditlog',
            'icons',
        ],
        'hosts': hosts_items,
        'maintenance': maintenance_items,
        'services': [
            'wato.py?mode=rulesets&group=monconf',
            'wato.py?mode=rulesets&group=checkparams',
            'wato.py?mode=rulesets&group=activechecks',
            'wato.py?mode=rulesets&group=custom_checks',
            'static_checks',
            'service_groups',
            'check_plugins',
        ],
        'bi': ['bi_packs'],
        'users': users_items,
    }


@pytest.mark.usefixtures("register_builtin_html", "load_plugins", "with_admin_login")
def test_get_wato_menu_items():
    items_by_topic: Dict[str, List[str]] = {}
    for topic in get_wato_menu_items():
        items = items_by_topic.setdefault(topic.name, [])
        for item in topic.items:
            items.append(item.name)

    assert expected_items() == items_by_topic
