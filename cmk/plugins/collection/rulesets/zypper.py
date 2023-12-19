#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import (
    CheckParameterRuleSpecWithoutItem,
    DictElement,
    Dictionary,
    Localizable,
    Migrate,
    ServiceState,
    Topic,
)


def _parameter_form_zypper() -> Dictionary:
    return Dictionary(
        elements={
            "security": DictElement(
                parameter_form=ServiceState(
                    title=Localizable("State when security updates are pending"),
                    prefill_value=ServiceState.CRIT,
                ),
            ),
            "recommended": DictElement(
                parameter_form=ServiceState(
                    title=Localizable("State when recommended updates are pending"),
                    prefill_value=ServiceState.WARN,
                ),
            ),
            "other": DictElement(
                parameter_form=ServiceState(
                    title=Localizable(
                        "State when updates are pending, which are neither recommended or a "
                        "security update"
                    ),
                    prefill_value=ServiceState.OK,
                ),
            ),
            "locks": DictElement(
                parameter_form=ServiceState(
                    title=Localizable("State when packages are locked"),
                    prefill_value=ServiceState.WARN,
                ),
            ),
        },
        # TODO remove before 2.3 release, showcases migration
        transform=Migrate(raw_to_form=lambda v: v if isinstance(v, dict) and v else {}),
    )


rule_spec_zypper = CheckParameterRuleSpecWithoutItem(
    name="zypper",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_zypper,
    title=Localizable("Zypper Updates"),
)
