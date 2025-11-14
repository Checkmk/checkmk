#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

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


def _parameter_form_lldp_cache() -> Dictionary:
    remove_columns = [
        MultipleChoiceElement(name="port_description", title=Title("Neighbor port description")),
        MultipleChoiceElement(name="system_description", title=Title("Neighbor description")),
        MultipleChoiceElement(
            name="capabilities_map_supported", title=Title("Capabilities map supported")
        ),
        MultipleChoiceElement(name="capabilities", title=Title("Capabilities")),
    ]

    return Dictionary(
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
            "removecolumns": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Columns to remove"),
                    elements=remove_columns,
                )
            ),
            "use_short_if_name": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("use short interface names (i.e. Gi0/0 for GigabitEthernet0/0)"),
                    label=Label("enabled"),
                )
            ),
            "one_neighbour_per_port": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Accept only one neighbor per local port"),
                    label=Label("enabled"),
                )
            ),
        }
    )


rule_spec_inv_lldp_cache = InventoryParameters(
    name="inv_lldp_cache",
    parameter_form=_parameter_form_lldp_cache,
    title=Title("LLDP cache"),
    topic=Topic.NETWORKING,
)
