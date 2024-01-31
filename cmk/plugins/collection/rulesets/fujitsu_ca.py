#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Localizable, rule_specs


def _form_inventory_fujitsu_ca_ports() -> form_specs.composed.Dictionary:
    return form_specs.composed.Dictionary(
        elements={
            "indices": form_specs.composed.DictElement(
                parameter_form=form_specs.composed.List(
                    title=Localizable("CA port indices"),
                    parameter_form=form_specs.basic.Text(),
                )
            ),
            "modes": form_specs.composed.DictElement(
                parameter_form=form_specs.composed.MultipleChoice(
                    title=Localizable("CA port modes"),
                    elements=[
                        form_specs.composed.MultipleChoiceElement(
                            name="CA", title=Localizable("CA")
                        ),
                        form_specs.composed.MultipleChoiceElement(
                            name="RA", title=Localizable("RA")
                        ),
                        form_specs.composed.MultipleChoiceElement(
                            name="CARA", title=Localizable("CARA")
                        ),
                        form_specs.composed.MultipleChoiceElement(
                            name="Initiator", title=Localizable("Initiator")
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_inventory_fujitsu_ca_ports = rule_specs.DiscoveryParameters(
    title=Localizable("Fujitsu storage CA port discovery"),
    topic=rule_specs.Topic.GENERAL,
    eval_type=rule_specs.EvalType.MERGE,
    name="inventory_fujitsu_ca_ports",
    parameter_form=_form_inventory_fujitsu_ca_ports,
)
