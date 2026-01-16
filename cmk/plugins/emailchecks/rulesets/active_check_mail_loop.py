#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    SimpleLevels,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic

from . import options


def _migrate(value: object) -> Mapping[str, object]:
    """remove optional and add mandatory fields

    >>> _migrate({
    ...     "item": "MyItem",
    ...     "mail_from": "",
    ...     "mail_to": "mail@to.me",
    ... })
    {'delete_messages': False, 'item': 'MyItem', 'mail_to': 'mail@to.me'}

    """
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict, got {type(value)}")
    return {
        "delete_messages": False,
        **{k: v for k, v in value.items() if not k.startswith("mail_") or v},
    }


def _valuespec_active_checks_mail_loop() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This active check sends out special emails to a defined mail address using either "
            "the SMTP protocol or an EWS connection and then tries to receive these mails back "
            "by querying the inbox of an IMAP, POP3 or EWS mailbox. With this check you can "
            "verify that your whole mail delivery progress is working."
        ),
        elements={
            "item": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Name"),
                    help_text=Help("The service name will be <b>Mail Loop</b> plus this name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "subject": DictElement(
                parameter_form=String(
                    title=Title("Subject"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    help_text=Help(
                        "Here you can specify the subject text "
                        "instead of default text 'Check_MK-Mail-Loop'."
                    ),
                ),
            ),
            "send": DictElement(
                required=True,
                parameter_form=options.sending(),
            ),
            "fetch": DictElement(
                required=True,
                parameter_form=options.fetching({"IMAP", "POP3", "EWS", "GRAPHAPI"}),
            ),
            "mail_from": DictElement(
                parameter_form=String(
                    title=Title("From: email address"),
                    custom_validate=(validators.EmailAddress(),),
                ),
            ),
            "mail_to": DictElement(
                parameter_form=String(
                    title=Title("Destination email address"),
                    custom_validate=(validators.EmailAddress(),),
                ),
            ),
            "connect_timeout": DictElement(
                parameter_form=options.timeout(),
            ),
            "duration": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Loop duration"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((30.0, 60.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "delete_messages": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Delete processed messages"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "Delete all messages identified as being related to this "
                        "check. This is disabled by default, which will make "
                        "your mailbox grow when you do not clean it up on your own."
                    ),
                ),
            ),
        },
        migrate=_migrate,
    )


rule_spec_active_check_mail_loop = ActiveCheck(
    name="mail_loop",
    title=Title("Check email delivery"),
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_active_checks_mail_loop,
)
