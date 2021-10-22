#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

from cmk.gui.watolib.main_menu import main_module_registry


def test_registered_modules():
    expected_modules = [
        "folder",
        "tags",
        "globalvars",
        "host_attrs",
        "wato.py?group=static&mode=rulesets",
        "check_plugins",
        "read_only",
        "predefined_conditions",
        "host_groups",
        "service_groups",
        "users",
        "user_attrs",
        "roles",
        "contact_groups",
        "notifications",
        "timeperiods",
        "mkeventd_rule_packs",
        "bi_packs",
        "sites",
        "backup",
        "passwords",
        "analyze_config",
        "auditlog",
        "icons",
        "background_jobs_overview",
        "ldap_config",
        "diagnostics",
        "download_agents",
        "rule_search",
        "wato.py?group=activechecks&mode=rulesets",
        "wato.py?group=agent&mode=rulesets",
        "wato.py?group=agents&mode=rulesets",
        "wato.py?group=checkparams&mode=rulesets",
        "wato.py?group=custom_checks&mode=rulesets",
        "wato.py?group=datasource_programs&mode=rulesets",
        "wato.py?group=inventory&mode=rulesets",
        "wato.py?group=monconf&mode=rulesets",
        "wato.py?group=host_monconf&mode=rulesets",
        "wato.py?group=snmp&mode=rulesets",
        "wato.py?group=vm_cloud_container&mode=rulesets",
        "wato.py?group=eventconsole&mode=rulesets",
    ]

    if cmk_version.is_raw_edition():
        expected_modules += [
            "download_agents_linux",
            "download_agents_windows",
        ]

    if not cmk_version.is_raw_edition():
        expected_modules += [
            "agent_registration",
            "agents",
            "alert_handlers",
            "dcd_connections",
            "influxdb_connections",
            "license_usage",
            "mkps",
        ]

    if cmk_version.is_managed_edition():
        expected_modules += [
            "customer_management",
        ]

    assert sorted(m().mode_or_url for m in main_module_registry.values()) == sorted(
        expected_modules
    )
