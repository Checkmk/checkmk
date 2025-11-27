#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import InventoryParameters, Topic


def _migrate_remove_columns(value: object) -> Sequence[str]:
    if isinstance(value, list):
        # Ensure we return a Sequence[str] and remove "last_change".
        return [v for v in value if isinstance(v, str) and v != "last_change"]
    return []


def _migrate_cdp_cache(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        if "removecolumns" in value.keys():
            value["remove_columns"] = value.pop("removecolumns")

        if "remove_columns" not in value.keys() or not isinstance(value["remove_columns"], list):
            value["remove_columns"] = []

        return value
    return {}


_remove_columns = [
    MultipleChoiceElement(name="platform_details", title=Title("Neighbor platform details")),
    MultipleChoiceElement(name="capabilities", title=Title("Capabilities")),
    MultipleChoiceElement(name="vtp_mgmt_domain", title=Title("VTP domain")),
    MultipleChoiceElement(name="native_vlan", title=Title("Native VLAN")),
    MultipleChoiceElement(name="duplex", title=Title("Duplex")),
    MultipleChoiceElement(name="power_consumption", title=Title("Power level")),
    MultipleChoiceElement(name="platform", title=Title("Neighbor platform")),
]


def parameter_form_cdp_cache() -> Dictionary:
    return Dictionary(
        migrate=_migrate_cdp_cache,
        elements={
            "remove_domain": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Remove domain name from neighbor device name"),
                    label=Label("enabled"),
                )
            ),
            "domain_name": DictElement(
                parameter_form=String(
                    title=Title("Specific domain name to remove from neighbor device name"),
                )
            ),
            "remove_columns": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Columns to remove"),
                    elements=_remove_columns,
                    migrate=_migrate_remove_columns,
                )
            ),
            "use_short_if_name": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Use short interface names (i.e. Gi0/0 for GigabitEthernet0/0)"),
                    label=Label("enabled"),
                )
            ),
        },
    )


rule_spec_inv_cdp_cache = InventoryParameters(
    name="inv_cdp_cache",
    parameter_form=parameter_form_cdp_cache,
    title=Title("CDP cache"),
    topic=Topic.NETWORKING,
)
