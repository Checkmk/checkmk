#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.http import request

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_proxy,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import MatchRegex

from ._helpers import _get_url_prefix_setting


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Push notification parameters"),
        elements={
            "api_key": DictElement(
                parameter_form=String(
                    title=Title("API key"),
                    help_text=Help(
                        "You need to provide a valid API key to be able to send push notifications "
                        'using Pushover. Register and login to <a href="https://www.pushover.net" '
                        'target="_blank">Pushover</a>, thn create your Checkmk installation as '
                        "application and obtain your API key."
                    ),
                    custom_validate=[
                        MatchRegex(
                            regex="^[a-zA-Z0-9]{30,40}$",
                            error_msg=Message("Invalid API key"),
                        ),
                    ],
                ),
                required=True,
            ),
            "recipient_key": DictElement(
                parameter_form=String(
                    title=Title("User / Group Key"),
                    help_text=Help(
                        "Configure the user or group to receive the notifications by providing "
                        "the user or group key here. The key can be obtained from the Pushover "
                        "website."
                    ),
                    custom_validate=[
                        MatchRegex(
                            regex="^[a-zA-Z0-9]{30,40}$",
                            error_msg=Message("Invalid user / group key"),
                        ),
                    ],
                ),
                required=True,
            ),
            "url_prefix": _get_url_prefix_setting(
                default_value="automatic_https" if request.is_ssl_request else "automatic_http",
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
            "priority": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Priority"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="emergency",
                            title=Title(
                                "Emergency: Repeat push notification in intervalls till expire time."
                            ),
                            parameter_form=Tuple(
                                elements=[
                                    TimeSpan(
                                        title=Title("Retry time"),
                                        displayed_magnitudes=[
                                            TimeMagnitude.DAY,
                                            TimeMagnitude.HOUR,
                                            TimeMagnitude.MINUTE,
                                            TimeMagnitude.SECOND,
                                        ],
                                    ),
                                    TimeSpan(
                                        title=Title("Expire time"),
                                        displayed_magnitudes=[
                                            TimeMagnitude.DAY,
                                            TimeMagnitude.HOUR,
                                            TimeMagnitude.MINUTE,
                                            TimeMagnitude.SECOND,
                                        ],
                                    ),
                                    String(
                                        title=Title("Receipt"),
                                        help_text=Help(
                                            "The receipt can be used to periodically poll receipts API to get "
                                            "the status of the notification. "
                                            'See <a href="https://pushover.net/api#receipt" target="_blank">'
                                            "Pushover receipts and callbacks</a> for more information."
                                        ),
                                        custom_validate=[
                                            MatchRegex(
                                                regex="^[a-zA-Z0-9]{30,40}$",
                                                error_msg=Message("Invalid receipt"),
                                            ),
                                        ],
                                    ),
                                ]
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="high",
                            title=Title("High: Push notification alerts bypass quiet hours"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="normal",
                            title=Title("Normal: Regular push notification (default)"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="low",
                            title=Title("Low: No sound/vibration but show popup"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="lowest",
                            title=Title("Lowest: No notification, update badge number"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue("normal"),
                    migrate=_migrate_to_priority,
                ),
            ),
            "sound": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Select sound"),
                    help_text=Help(
                        'See <a href="https://pushover.net/api#sounds" target="_blank">'
                        "Pushover sounds</a> for more information and trying out available sounds."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="none",
                            title=Title("None (silent)"),
                        ),
                        SingleChoiceElement(
                            name="alien",
                            title=Title("Alien Alarm (long)"),
                        ),
                        SingleChoiceElement(
                            name="bike",
                            title=Title("Bike"),
                        ),
                        SingleChoiceElement(
                            name="bugle",
                            title=Title("Bugle"),
                        ),
                        SingleChoiceElement(
                            name="cashregister",
                            title=Title("Cash Register"),
                        ),
                        SingleChoiceElement(
                            name="classical",
                            title=Title("Classical"),
                        ),
                        SingleChoiceElement(
                            name="climb",
                            title=Title("Climb (long)"),
                        ),
                        SingleChoiceElement(
                            name="cosmic",
                            title=Title("Cosmic"),
                        ),
                        SingleChoiceElement(
                            name="echo",
                            title=Title("Pushover Echo (long)"),
                        ),
                        SingleChoiceElement(
                            name="falling",
                            title=Title("Falling"),
                        ),
                        SingleChoiceElement(
                            name="gamelan",
                            title=Title("Gamelan"),
                        ),
                        SingleChoiceElement(
                            name="incoming",
                            title=Title("Incoming"),
                        ),
                        SingleChoiceElement(
                            name="intermission",
                            title=Title("Intermission"),
                        ),
                        SingleChoiceElement(
                            name="magic",
                            title=Title("Magic"),
                        ),
                        SingleChoiceElement(
                            name="mechanical",
                            title=Title("Mechanical"),
                        ),
                        SingleChoiceElement(
                            name="persistent",
                            title=Title("Persistent (long)"),
                        ),
                        SingleChoiceElement(
                            name="pianobar",
                            title=Title("Piano Bar"),
                        ),
                        SingleChoiceElement(
                            name="pushover",
                            title=Title("Pushover"),
                        ),
                        SingleChoiceElement(
                            name="siren",
                            title=Title("Siren"),
                        ),
                        SingleChoiceElement(
                            name="spacealarm",
                            title=Title("Space Alarm"),
                        ),
                        SingleChoiceElement(
                            name="tugboat",
                            title=Title("Tug Boat"),
                        ),
                        SingleChoiceElement(
                            name="updown",
                            title=Title("Up Down (long)"),
                        ),
                        SingleChoiceElement(
                            name="vibrate",
                            title=Title("Vibrate only"),
                        ),
                    ],
                    prefill=DefaultValue("none"),
                ),
            ),
        },
    )


# TODO add typing
def _migrate_to_priority(value):
    # Already migrated
    if isinstance(value, tuple):
        return value

    if isinstance(value, dict):
        assert isinstance(value["retry"], int)
        assert isinstance(value["expire"], int)
        assert value["receipts"] is not None and isinstance(value["receipts"], str)
        return ("emergency", (float(value["retry"]), float(value["expire"]), value["receipts"]))

    if value == "0":
        return ("normal", None)

    if value == "1":
        return ("high", None)

    if value == "-1":
        return ("low", None)

    if value == "-2":
        return ("lowest", None)

    raise ValueError(f"Invalid priority format: {value}")
