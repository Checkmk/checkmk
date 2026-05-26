#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui import main_modules
from cmk.gui.rule_specs.legacy_converter import GENERATED_GROUP_PREFIX
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry


@pytest.fixture(scope="module", autouse=True)
def _load_gui_plugins() -> None:
    """Run the gui edition's full plug-in registration chain so the rulespec
    registries are populated with the production set the snapshots assert on.
    """
    main_modules.register(Edition.COMMUNITY)


def _is_dynamically_generated_group(group_name: str) -> bool:
    # generated for the RulesetAPI v1
    return group_name.rsplit("/", maxsplit=1)[-1].startswith(GENERATED_GROUP_PREFIX)


def test_rulespec_group_choices() -> None:
    assert {
        g
        for g in rulespec_group_registry.get_group_choices()
        if not _is_dynamically_generated_group(g[0])
    } == {
        ("activechecks", "HTTP, TCP, email, ..."),
        ("agent", "Access to agents"),
        ("agent/check_mk_agent", "&nbsp;&nbsp;⌙ Checkmk agent"),
        ("agent/general_settings", "&nbsp;&nbsp;⌙ General Settings"),
        ("agents", "Agent rules"),
        ("agents/generic_options", "&nbsp;&nbsp;⌙ Generic agent options"),
        ("checkparams", "Service discovery rules"),
        ("checkparams/discovery", "&nbsp;&nbsp;⌙ Discovery of individual services"),
        (
            "checkparams/inventory_and_check_mk_settings",
            "&nbsp;&nbsp;⌙ Discovery and Checkmk settings",
        ),
        ("datasource_programs", "Other integrations"),
        ("eventconsole", "Event Console rules"),
        ("inventory", "HW/SW inventory"),
        ("host_monconf", "Host monitoring rules"),
        ("host_monconf/host_checks", "&nbsp;&nbsp;⌙ Host checks"),
        ("host_monconf/host_notifications", "&nbsp;&nbsp;⌙ Notifications"),
        ("host_monconf/host_various", "&nbsp;&nbsp;⌙ Various"),
        ("monconf", "Service monitoring rules"),
        ("monconf/applications", "&nbsp;&nbsp;⌙ Applications, Processes & Services"),
        ("monconf/networking", "&nbsp;&nbsp;⌙ Networking"),
        ("monconf/os", "&nbsp;&nbsp;⌙ Operating System Resources"),
        ("monconf/printers", "&nbsp;&nbsp;⌙ Printers"),
        ("monconf/storage", "&nbsp;&nbsp;⌙ Storage, file systems and files"),
        (
            "monconf/environment",
            "&nbsp;&nbsp;⌙ Temperature, Humidity, Electrical Parameters, etc.",
        ),
        ("monconf/hardware", "&nbsp;&nbsp;⌙ Hardware, BIOS"),
        ("monconf/virtualization", "&nbsp;&nbsp;⌙ Virtualization"),
        ("monconf/notifications", "&nbsp;&nbsp;⌙ Notifications"),
        ("monconf/service_checks", "&nbsp;&nbsp;⌙ Service Checks"),
        ("monconf/various", "&nbsp;&nbsp;⌙ Various"),
        ("custom_checks", "Other services"),
        ("datasource_programs/apps", "&nbsp;&nbsp;⌙ Applications"),
        ("datasource_programs/cloud", "&nbsp;&nbsp;⌙ Cloud based environments"),
        ("datasource_programs/container", "&nbsp;&nbsp;⌙ Containerization"),
        ("datasource_programs/custom", "&nbsp;&nbsp;⌙ Custom integrations"),
        ("datasource_programs/hw", "&nbsp;&nbsp;⌙ Hardware"),
        ("datasource_programs/os", "&nbsp;&nbsp;⌙ Operating systems"),
        ("datasource_programs/testing", "&nbsp;&nbsp;⌙ Testing"),
        ("snmp", "SNMP rules"),
        ("static", "Enforced services"),
        ("static/applications", "&nbsp;&nbsp;⌙ Applications, Processes & Services"),
        ("static/environment", "&nbsp;&nbsp;⌙ Temperature, Humidity, Electrical Parameters, etc."),
        ("static/hardware", "&nbsp;&nbsp;⌙ Hardware, BIOS"),
        ("static/networking", "&nbsp;&nbsp;⌙ Networking"),
        ("static/os", "&nbsp;&nbsp;⌙ Operating System Resources"),
        ("static/printers", "&nbsp;&nbsp;⌙ Printers"),
        ("static/storage", "&nbsp;&nbsp;⌙ Storage, file systems and files"),
        ("static/virtualization", "&nbsp;&nbsp;⌙ Virtualization"),
        ("vm_cloud_container", "VM, cloud, container"),
    }


def test_rulespec_get_all_groups() -> None:
    assert {
        g for g in rulespec_registry.get_all_groups() if not _is_dynamically_generated_group(g)
    } == {
        "activechecks",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "monconf/applications",
        "monconf/environment",
        "monconf/hardware",
        "monconf/service_checks",
        "monconf/networking",
        "monconf/notifications",
        "monconf/os",
        "monconf/printers",
        "monconf/storage",
        "monconf/various",
        "monconf/virtualization",
        "agent/general_settings",
        "agent/check_mk_agent",
        "agents/generic_options",
        "custom_checks",
        "snmp",
        "vm_cloud_container",
        "checkparams/inventory_and_check_mk_settings",
        "static/networking",
        "static/applications",
        "checkparams/discovery",
        "static/environment",
        "static/storage",
        "static/printers",
        "static/os",
        "static/virtualization",
        "static/hardware",
        "datasource_programs/apps",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "inventory",
        "eventconsole",
    }
