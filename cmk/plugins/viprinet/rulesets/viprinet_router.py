#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, SingleChoice, SingleChoiceElement
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

_LEGACY_MODE_TO_IDENTIFIER = {
    "inv": "inventory",
    "0": "node",
    "1": "hub",
    "2": "hub_hotspare",
    "3": "hub_hotspare_replacing",
}


def _migrate_expect_mode(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Invalid value for 'expect_mode': {value!r}")
    if value in _LEGACY_MODE_TO_IDENTIFIER:
        return _LEGACY_MODE_TO_IDENTIFIER[value]
    if value in _LEGACY_MODE_TO_IDENTIFIER.values():
        return value
    raise ValueError(f"Invalid value for 'expect_mode': {value!r}")


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "expect_mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Set expected router mode"),
                    migrate=_migrate_expect_mode,
                    elements=[
                        SingleChoiceElement(
                            name="inventory", title=Title("Mode found during inventory")
                        ),
                        SingleChoiceElement(name="node", title=Title("Node")),
                        SingleChoiceElement(name="hub", title=Title("Hub")),
                        SingleChoiceElement(
                            name="hub_hotspare", title=Title("Hub running as HotSpare")
                        ),
                        SingleChoiceElement(
                            name="hub_hotspare_replacing",
                            title=Title("Hotspare-Hub replacing another router"),
                        ),
                    ],
                ),
            ),
        },
        ignored_elements=("mode_inv",),
    )


rule_spec_viprinet_router = CheckParameters(
    name="viprinet_router",
    topic=Topic.NETWORKING,
    condition=HostCondition(),
    parameter_form=_parameter_form,
    title=Title("Viprinet router"),
)
