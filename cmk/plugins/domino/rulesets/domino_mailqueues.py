#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    SingleChoice,
    SingleChoiceElement,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_domino_mailqueues() -> Dictionary:
    return Dictionary(
        elements={
            "queue_length": DictElement[SimpleLevelsConfigModel[int]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Number of mails in queue"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(
                        label=Label("mails"),
                        custom_validate=(validators.NumberInRange(0, None),),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((300, 350)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_domino_mailqueues = CheckParameters(
    name="domino_mailqueues",
    title=Title("Lotus Domino mail queues"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_domino_mailqueues,
    condition=HostAndItemCondition(
        item_title=Title("Mail queue name"),
        item_form=SingleChoice(
            elements=[
                SingleChoiceElement(name="lnDeadMail", title=Title("Mails in dead queue")),
                SingleChoiceElement(name="lnWaitingMail", title=Title("Mails in waiting queue")),
                SingleChoiceElement(name="lnMailHold", title=Title("Mails in hold queue")),
                SingleChoiceElement(name="lnMailTotalPending", title=Title("Total pending mails")),
                SingleChoiceElement(
                    name="InMailWaitingforDNS", title=Title("Mails waiting for DNS queue")
                ),
            ],
        ),
    ),
)
