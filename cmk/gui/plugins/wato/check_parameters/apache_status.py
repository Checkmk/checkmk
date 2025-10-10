#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.gui.form_specs.generators.tuple_utils import TupleLevels
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Integer,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _item_spec_apache_status():
    return String(
        title=Title("Apache Server"),
        help_text=Help("A string-combination of servername and port, e.g. 127.0.0.1:5000."),
        custom_validate=[LengthInRange(min_value=1)],
    )


def _parameter_form_spec_apache_status() -> Dictionary:
    return Dictionary(
        elements={
            "OpenSlots": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Remaining Open Slots"),
                    help_text=Help("Here you can set the number of remaining open slots"),
                    elements=[
                        Integer(title=Title("Warning below"), label=Label("slots")),
                        Integer(title=Title("Critical below"), label=Label("slots")),
                    ],
                ),
            ),
            "BusyWorkers": DictElement(
                required=False,
                parameter_form=TupleLevels(
                    title=Title("Busy workers"),
                    help_text=Help("Here you can set upper levels of busy workers"),
                    elements=[
                        Integer(title=Title("Warning at"), label=Label("busy workers")),
                        Integer(title=Title("Critical at"), label=Label("busy workers")),
                    ],
                ),
            ),
        }
    )


rule_spec_apache_status = CheckParameters(
    name="apache_status",
    title=Title("Apache Status"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_spec_apache_status,
    condition=HostAndItemCondition(
        item_title=Title("Apache Server"), item_form=_item_spec_apache_status()
    ),
)
