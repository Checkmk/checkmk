#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.generators.tuple_utils import TupleLevels
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Integer,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _item_spec_ad_replication() -> String:
    return String(
        title=Title("Replication Partner"),
        help_text=Help("The name of the replication partner (Destination DC Site/Destination DC)."),
        custom_validate=[LengthInRange(min_value=1)],
    )


def _form_spec_ad_replication() -> Dictionary:
    return Dictionary(
        elements={
            "failure_levels": DictElement(
                required=True,
                parameter_form=TupleLevels(
                    help_text=Help("Upper levels for the number of replication failures"),
                    elements=[
                        Integer(title=Title("Warning at failure count")),
                        Integer(title=Title("Critical at failure count")),
                    ],
                ),
            )
        }
    )


rule_spec_ad_replication = CheckParameters(
    name="ad_replication",
    title=Title("Active Directory Replication"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_ad_replication,
    condition=HostAndItemCondition(
        item_title=Title("Replication Partner"), item_form=_item_spec_ad_replication()
    ),
)
