#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import form_specs, Localizable, rule_specs


def _parameter_form_discover_rmon() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        elements={
            "discover": form_specs.DictElement(
                form_specs.BooleanChoice(
                    label=Localizable("Discover RMON statistics services"),
                    prefill_value=True,
                    help_text=Localizable(
                        "Enabling this option will result in an additional service for every RMON-capable "
                        "switch port. This service will provide detailed information on the distribution of "
                        "packet sizes transferred over the port. Note: currently, this additional RMON check "
                        "does not honor the inventory settings for switch ports."
                    ),
                ),
                required=True,
            )
        },
        transform=form_specs.Migrate(
            model_to_form=lambda p: p if isinstance(p, dict) else {"discover": p}
        ),
    )


rule_spec_rmon_discovery = rule_specs.DiscoveryParameters(
    name="rmon_discovery",
    title=Localizable("RMON statistics"),
    topic=rule_specs.Topic.GENERAL,
    parameter_form=_parameter_form_discover_rmon,
    eval_type=rule_specs.EvalType.MERGE,
)
