#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import register
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable
from cmk.base.plugins.agent_based.utils import netapp_api
from cmk.base.plugins.agent_based.utils import netapp_ontap_models as models

Section = Mapping[str, models.ShelfPsuModel]

# <<<netapp_ontap_psu:sep(0)>>>
# {"id": 0, "list_id": "10", "state": "ok"}
# {"id": 1, "list_id": "10", "state": "ok"}


def _get_section_single_instance(section: Section) -> netapp_api.SectionSingleInstance:
    error_key, number_key = netapp_api.DEV_KEYS["power supply unit"]

    return {
        key: {error_key: str(val.state == "error").lower(), number_key: key}
        for key, val in section.items()
    }


def parse_netapp_ontap_psu(string_table: StringTable) -> Section:
    """
    It should be parsed/discoverd evaluating with "installed"/"not installed" but the API is not
    responding with this information
    """

    return {
        psu.item_name(): psu
        for line in string_table
        if (psu := models.ShelfPsuModel(**json.loads(line[0])))
    }


register.agent_section(
    name="netapp_ontap_psu",
    parse_function=parse_netapp_ontap_psu,
)


def check_netapp_ontap_psu(item: str, section: Section) -> CheckResult:
    yield from netapp_api.get_single_check("power supply unit")(
        item, _get_section_single_instance(section)
    )


register.check_plugin(
    name="netapp_ontap_psu",
    service_name="Power Supply Shelf %s",
    sections=["netapp_ontap_psu"],
    discovery_function=netapp_api.discover_single,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_ontap_psu,
)


def check_netapp_ontap_psu_summary(
    item: str,
    section: Section,
) -> CheckResult:
    yield from netapp_api.get_summary_check("power supply unit")(
        item, _get_section_single_instance(section)
    )


register.check_plugin(
    name="netapp_ontap_psu_summary",
    service_name="Power Supply Shelf %s",
    sections=["netapp_ontap_psu"],
    discovery_function=netapp_api.discover_summary,
    discovery_ruleset_name="discovery_netapp_api_fan_rules",
    discovery_default_parameters={"mode": "single"},
    check_function=check_netapp_ontap_psu_summary,
)
