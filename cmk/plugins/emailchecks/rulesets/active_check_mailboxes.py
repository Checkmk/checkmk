#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic

from .options import fetching, timeout


def _valuespec_active_checks_mailboxes() -> Dictionary:
    return Dictionary(
        help_text=Help("This check monitors count and age of mails in mailboxes."),
        elements={
            "service_description": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service name"),
                    help_text=Help(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    custom_validate=(validators.LengthInRange(1, None),),
                    prefill=DefaultValue("Mailboxes"),
                ),
            ),
            "fetch": DictElement(
                required=True,
                parameter_form=fetching({"IMAP", "EWS"}),
            ),
            "connect_timeout": DictElement(
                parameter_form=timeout(),
            ),
            "age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Message Age of oldest messages"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ),
                    ),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "age_newest": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Message Age of newest messages"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ),
                    ),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "count": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Message Count"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "mailboxes": DictElement(
                parameter_form=List(
                    title=Title("Check only the listed mailboxes"),
                    help_text=Help(
                        "By default, all mailboxes are checked with these parameters. "
                        "If you specify mailboxes here, only those are monitored."
                    ),
                    element_template=String(),
                ),
            ),
        },
    )


rule_spec_check_mailboxes = ActiveCheck(
    title=Title("Check IMAP/EWS Mailboxes"),
    topic=Topic.APPLICATIONS,
    name="mailboxes",
    parameter_form=_valuespec_active_checks_mailboxes,
)
