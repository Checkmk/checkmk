#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import form_specs, Localizable, rule_specs
from cmk.rulesets.v1.form_specs import validators


def _migrate_to_cascading_single_choice(value: object) -> tuple[str, str]:
    if isinstance(value, str):
        if value.startswith("~"):
            return "pattern", value[1:]
        return "exact", value
    if value is None:
        return "all", ""

    if isinstance(value, tuple):
        return value

    raise TypeError(Localizable("Expected a tuple, got %s") % str(type(value)))


def _formspec_inventory_sap_values():
    return form_specs.Dictionary(
        elements={
            "match": form_specs.DictElement(
                parameter_form=form_specs.CascadingSingleChoice(
                    title=Localizable("Node Path Matching"),
                    elements=[
                        form_specs.CascadingSingleChoiceElement(
                            name="exact",
                            title=Localizable("Exact path of the node"),
                            parameter_form=form_specs.String(
                                title=Localizable("Exact path of the node"),
                                prefill=form_specs.DefaultValue(
                                    "SAP CCMS Monitor Templates/Dialog Overview/Dialog "
                                    "Response Time/ResponseTime"
                                ),
                            ),
                        ),
                        form_specs.CascadingSingleChoiceElement(
                            name="pattern",
                            title=Localizable("Regular expression matching the path"),
                            parameter_form=form_specs.RegularExpression(
                                title=Localizable("Regular expression matching the path"),
                                predefined_help_text=form_specs.MatchingScope.PREFIX,
                                help_text=Localizable(
                                    "This regex must match the <i>beginning</i> of the complete "
                                    "path of the node as reported by the agent"
                                ),
                            ),
                        ),
                        form_specs.CascadingSingleChoiceElement(
                            name="all",
                            title=Localizable("Match all nodes"),
                            parameter_form=form_specs.FixedValue(
                                title=Localizable("Match all nodes"), value=""
                            ),
                        ),
                    ],
                    prefill=form_specs.DefaultValue("exact"),
                    migrate=_migrate_to_cascading_single_choice,
                ),
                required=True,
            ),
            "limit_item_levels": form_specs.DictElement(
                parameter_form=form_specs.Integer(
                    title=Localizable("Limit Path Levels for Service Names"),
                    unit=Localizable("path levels"),
                    help_text=Localizable(
                        "The service descriptions of the inventorized services are named like the "
                        "paths in SAP. You can use this option to let the inventory function only "
                        "use the last x path levels for naming."
                    ),
                    custom_validate=validators.InRange(min_value=1),
                ),
                required=False,
            ),
        }
    )


rule_spec_inventory_sap_values = rule_specs.DiscoveryParameters(
    title=Localizable("SAP R/3 single value discovery"),
    name="inventory_sap_values",
    eval_type=rule_specs.EvalType.ALL,
    parameter_form=_formspec_inventory_sap_values,
    topic=rule_specs.Topic.GENERAL,
)
