#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.main_menu import main_module_registry, main_module_topic_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_main_modules() -> None:
    assert sorted(main_module_registry) == [
        "analyze_config",
        "analyze_notifications",
        "auditlog",
        "background_jobs_overview",
        "backup",
        "bi_packs",
        "certificate_overview",
        "check_plugins",
        "contact_groups",
        "diagnostics",
        "download_agents",
        "download_agents_linux",
        "download_agents_windows",
        "folder",
        "global_settings.py",
        "host_attrs",
        "host_groups",
        "icons",
        "ldap_config",
        "microsoft_entra_id_connections",
        "mkeventd_rule_packs",
        "notifications",
        "passwords",
        "performance_profiles",
        "predefined_conditions",
        "read_only",
        "roles",
        "rule_search",
        "service_groups",
        "sites",
        "tags",
        "test_notifications",
        "timeperiods",
        "user_attrs",
        "users",
        "wato.py?group=activechecks&mode=rulesets",
        "wato.py?group=agent&mode=rulesets",
        "wato.py?group=agents&mode=rulesets",
        "wato.py?group=checkparams&mode=rulesets",
        "wato.py?group=custom_checks&mode=rulesets",
        "wato.py?group=datasource_programs&mode=rulesets",
        "wato.py?group=eventconsole&mode=rulesets",
        "wato.py?group=host_monconf&mode=rulesets",
        "wato.py?group=inventory&mode=rulesets",
        "wato.py?group=monconf&mode=rulesets",
        "wato.py?group=snmp&mode=rulesets",
        "wato.py?group=static&mode=rulesets",
        "wato.py?group=vm_cloud_container&mode=rulesets",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aaws",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aazure_v2",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Agcp",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Akube_v2",
        "wato.py?mode=edit_configuration_bundles&varname=special_agents%3Aproxmox_ve",
    ]


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_main_module_topics() -> None:
    assert sorted(main_module_topic_registry) == [
        "agents",
        "bi",
        "events",
        "exporter",
        "general",
        "hosts",
        "maintenance",
        "quick_setups",
        "services",
        "users",
    ]
