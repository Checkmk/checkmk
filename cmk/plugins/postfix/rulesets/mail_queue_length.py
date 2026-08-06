#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
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
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _queue_levels(
    title: Title, help_text: Help, default: tuple[int, int]
) -> DictElement[SimpleLevelsConfigModel[int]]:
    return DictElement(
        required=False,
        parameter_form=SimpleLevels(
            title=title,
            help_text=help_text,
            level_direction=LevelDirection.UPPER,
            form_spec_template=Integer(
                label=Label("mails"),
                custom_validate=(validators.NumberInRange(0, None),),
            ),
            prefill_levels_type=DefaultValue(LevelsType.FIXED),
            prefill_fixed_levels=DefaultValue(default),
            migrate=migrate_to_integer_simple_levels,
        ),
    )


def _parameter_form_mail_queue_length() -> Dictionary:
    return Dictionary(
        elements={
            "deferred": _queue_levels(
                Title("Mails in outgoing mail queue/deferred mails"),
                Help(
                    "This rule is applied to the number of emails currently in the deferred "
                    "mail queue, or in the general outgoing mail queue, if such a "
                    "distinction is not available."
                ),
                (10, 20),
            ),
            "active": _queue_levels(
                Title("Mails in active mail queue"),
                Help(
                    "This rule is applied to the number of emails currently in the active "
                    "mail queue."
                ),
                (800, 1000),
            ),
            "failed": _queue_levels(
                Title("Mails in failed mail queue"),
                Help(
                    "This rule is applied to the number of emails currently in the failed "
                    "mail queue."
                ),
                (1, 1),
            ),
        },
    )


rule_spec_mail_queue_length = CheckParameters(
    name="mail_queue_length",
    title=Title("Mails in outgoing mail queue (multiple queues)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mail_queue_length,
    condition=HostAndItemCondition(item_title=Title("Mail queue name"), item_form=String()),
)
