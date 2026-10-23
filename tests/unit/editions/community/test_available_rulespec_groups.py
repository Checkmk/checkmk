#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.rule_specs.legacy_converter import GENERATED_GROUP_PREFIX
from cmk.gui.watolib.rulespecs import rulespec_group_registry


def _is_dynamically_generated_group(group_name: str) -> bool:
    # generated for the RulesetAPI v1
    return group_name.rsplit("/", maxsplit=1)[-1].startswith(GENERATED_GROUP_PREFIX)


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_rulespec_groups() -> None:
    assert sorted(g for g in rulespec_group_registry if not _is_dynamically_generated_group(g)) == [
        "activechecks",
        "agent",
        "agent/check_mk_agent",
        "agent/general_settings",
        "agents",
        "agents/generic_options",
        "checkparams",
        "checkparams/discovery",
        "checkparams/inventory_and_check_mk_settings",
        "custom_checks",
        "datasource_programs",
        "datasource_programs/apps",
        "datasource_programs/cloud",
        "datasource_programs/container",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "datasource_programs/testing",
        "eventconsole",
        "host_monconf",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "inventory",
        "monconf",
        "monconf/applications",
        "monconf/environment",
        "monconf/hardware",
        "monconf/networking",
        "monconf/notifications",
        "monconf/os",
        "monconf/printers",
        "monconf/service_checks",
        "monconf/storage",
        "monconf/various",
        "monconf/virtualization",
        "snmp",
        "static",
        "static/applications",
        "static/environment",
        "static/hardware",
        "static/networking",
        "static/os",
        "static/printers",
        "static/storage",
        "static/virtualization",
        "vm_cloud_container",
    ]
