#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, rule_specs, Title


def _form_inventory_fujitsu_ca_ports() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        elements={
            "indices": form_specs.DictElement(
                parameter_form=form_specs.List(
                    title=Title("CA port indices"),
                    element_template=form_specs.String(),
                )
            ),
            "modes": form_specs.DictElement(
                parameter_form=form_specs.MultipleChoice(
                    title=Title("CA port modes"),
                    elements=[
                        form_specs.MultipleChoiceElement(name="CA", title=Title("CA")),
                        form_specs.MultipleChoiceElement(name="RA", title=Title("RA")),
                        form_specs.MultipleChoiceElement(name="CARA", title=Title("CARA")),
                        form_specs.MultipleChoiceElement(
                            name="Initiator", title=Title("Initiator")
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_inventory_fujitsu_ca_ports = rule_specs.DiscoveryParameters(
    title=Title("Fujitsu storage CA port discovery"),
    topic=rule_specs.Topic.GENERAL,
    name="inventory_fujitsu_ca_ports",
    parameter_form=_form_inventory_fujitsu_ca_ports,
)
