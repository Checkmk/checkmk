#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import cmk.utils.version as cmk_version
from cmk.gui.watolib.main_menu import main_module_registry

pytestmark = pytest.mark.usefixtures("load_plugins")


def test_registered_modules():
    expected_modules = [
        'folder',
        'tags',
        'globalvars',
        'host_attrs',
        'wato.py?mode=rulesets&group=static',
        'check_plugins',
        'read_only',
        'predefined_conditions',
        'host_groups',
        'service_groups',
        'users',
        'user_attrs',
        'roles',
        'contact_groups',
        'notifications',
        'timeperiods',
        'mkeventd_rule_packs',
        'bi_packs',
        'sites',
        'backup',
        'passwords',
        'analyze_config',
        'auditlog',
        'icons',
        'background_jobs_overview',
        'ldap_config',
        'diagnostics',
        'download_agents',
        'version.py',
        'rule_search',
        'wato.py?mode=rulesets&group=activechecks',
        'wato.py?mode=rulesets&group=agent',
        'wato.py?mode=rulesets&group=checkparams',
        'wato.py?mode=rulesets&group=custom_checks',
        'wato.py?mode=rulesets&group=datasource_programs',
        'wato.py?mode=rulesets&group=inventory',
        'wato.py?mode=rulesets&group=monconf',
        'wato.py?mode=rulesets&group=host_monconf',
        'wato.py?mode=rulesets&group=snmp',
        'wato.py?mode=rulesets&group=vm_cloud_container',
    ]

    if cmk_version.is_raw_edition():
        expected_modules += [
            'download_agents_linux',
            'download_agents_windows',
        ]

    if not cmk_version.is_raw_edition():
        expected_modules += [
            'agents',
            'alert_handlers',
            'mkps',
            'license_usage',
            'dcd_connections',
        ]

    if cmk_version.is_managed_edition():
        expected_modules += [
            "customer_management",
        ]

    assert sorted(
        m().mode_or_url for m in main_module_registry.values()) == sorted(expected_modules)
