#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    IgnoreResultsError,
    Result,
    RuleSetType,
    State,
)
from cmk.plugins.lib.fileinfo import (
    check_fileinfo_data,
    check_fileinfo_groups_data,
    discovery_fileinfo,
    discovery_fileinfo_groups,
    Fileinfo,
    parse_fileinfo,
)


def check_sap_hana_fileinfo(item: str, params: Mapping[str, Any], section: Fileinfo) -> CheckResult:
    reftime = section.reftime
    if reftime is None:
        yield Result(state=State.UNKNOWN, summary="Missing reference timestamp")
        return

    file_info_item = section.files.get(item)
    if not file_info_item:
        raise IgnoreResultsError("Login into database failed.")

    yield from check_fileinfo_data(file_info_item, reftime, params)


def check_sap_hana_fileinfo_groups(
    item: str, params: Mapping[str, Any], section: Fileinfo
) -> CheckResult:
    reftime = section.reftime
    if reftime is None:
        yield Result(state=State.UNKNOWN, summary="Missing reference timestamp")
        return

    if not section.files:
        raise IgnoreResultsError("Login into database failed.")

    yield from check_fileinfo_groups_data(item, params, section, reftime)


agent_section_sap_hana_fileinfo = AgentSection(
    name="sap_hana_fileinfo",
    parse_function=parse_fileinfo,
)

check_plugin_sap_hana_fileinfo = CheckPlugin(
    name="sap_hana_fileinfo",
    service_name="File %s",
    discovery_function=discovery_fileinfo,
    discovery_ruleset_name="fileinfo_groups",
    discovery_default_parameters={},
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_sap_hana_fileinfo,
    check_default_parameters={},
    check_ruleset_name="fileinfo",
)

check_plugin_sap_hana_fileinfo_groups = CheckPlugin(
    name="sap_hana_fileinfo_groups",
    sections=["sap_hana_fileinfo"],
    service_name="File group %s",
    discovery_function=discovery_fileinfo_groups,
    discovery_ruleset_name="fileinfo_groups",
    discovery_default_parameters={},
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_sap_hana_fileinfo_groups,
    check_default_parameters={},
    check_ruleset_name="fileinfo_groups_checking",
)
