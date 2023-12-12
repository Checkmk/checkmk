#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.wato import HTTPProxyReference

from ._base import NotificationParameter
from ._helpers import local_site_url


class NotificationParameterPushover(NotificationParameter):
    @property
    def ident(self) -> str:
        return "pushover"

    @property
    def spec(self):
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["url_prefix", "proxy_url", "priority", "sound"],
            elements=[
                (
                    "api_key",
                    TextInput(
                        title=_("API Key"),
                        help=_(
                            "You need to provide a valid API key to be able to send push notifications "
                            'using Pushover. Register and login to <a href="https://www.pushover.net" '
                            'target="_blank">Pushover</a>, thn create your Checkmk installation as '
                            "application and obtain your API key."
                        ),
                        size=40,
                        allow_empty=False,
                        regex="^[a-zA-Z0-9]{30,40}$",
                    ),
                ),
                (
                    "recipient_key",
                    TextInput(
                        title=_("User / Group Key"),
                        help=_(
                            "Configure the user or group to receive the notifications by providing "
                            "the user or group key here. The key can be obtained from the Pushover "
                            "website."
                        ),
                        size=40,
                        allow_empty=False,
                        regex="^[a-zA-Z0-9]{30,40}$",
                    ),
                ),
                (
                    "url_prefix",
                    TextInput(
                        title=_("URL prefix for links to Checkmk"),
                        help=_(
                            "If you specify an URL prefix here, then several parts of the "
                            "email body are armed with hyperlinks to your Checkmk GUI, so "
                            "that the recipient of the email can directly visit the host or "
                            "service in question in Checkmk. Specify an absolute URL including "
                            "the <tt>.../check_mk/</tt>"
                        ),
                        regex="^(http|https)://.*/check_mk/$",
                        regex_error=_(
                            "The URL must begin with <tt>http</tt> or "
                            "<tt>https</tt> and end with <tt>/check_mk/</tt>."
                        ),
                        size=64,
                        default_value=local_site_url,
                    ),
                ),
                (
                    "proxy_url",
                    HTTPProxyReference(),
                ),
                (
                    "priority",
                    Transform(
                        valuespec=CascadingDropdown(
                            title=_("Priority"),
                            choices=[
                                (
                                    "2",
                                    _(
                                        "Emergency: Repeat push notification in intervalls till expire time."
                                    ),
                                    Tuple(
                                        elements=[
                                            Age(title=_("Retry time")),
                                            Age(title=_("Expire time")),
                                            TextInput(
                                                title=_("Receipt"),
                                                help=_(
                                                    "The receipt can be used to periodically poll receipts API to get "
                                                    "the status of the notification. "
                                                    'See <a href="https://pushover.net/api#receipt" target="_blank">'
                                                    "Pushover receipts and callbacks</a> for more information."
                                                ),
                                                size=40,
                                                regex="[a-zA-Z0-9]{0,30}",
                                            ),
                                        ]
                                    ),
                                ),
                                ("1", _("High: Push notification alerts bypass quiet hours")),
                                ("0", _("Normal: Regular push notification (default)")),
                                ("-1", _("Low: No sound/vibration but show popup")),
                                ("-2", _("Lowest: No notification, update badge number")),
                            ],
                            default_value="0",
                        ),
                        to_valuespec=self._transform_to_pushover_priority,
                        from_valuespec=self._transform_from_pushover_priority,
                    ),
                ),
                (
                    "sound",
                    DropdownChoice(
                        title=_("Select sound"),
                        help=_(
                            'See <a href="https://pushover.net/api#sounds" target="_blank">'
                            "Pushover sounds</a> for more information and trying out available sounds."
                        ),
                        choices=[
                            ("none", _("None (silent)")),
                            ("alien", _("Alien Alarm (long)")),
                            ("bike", _("Bike")),
                            ("bugle", _("Bugle")),
                            ("cashregister", _("Cash Register")),
                            ("classical", _("Classical")),
                            ("climb", _("Climb (long)")),
                            ("cosmic", _("Cosmic")),
                            ("echo", _("Pushover Echo (long)")),
                            ("falling", _("Falling")),
                            ("gamelan", _("Gamelan")),
                            ("incoming", _("Incoming")),
                            ("intermission", _("Intermission")),
                            ("magic", _("Magic")),
                            ("mechanical", _("Mechanical")),
                            ("persistent", _("Persistent (long)")),
                            ("pianobar", _("Piano Bar")),
                            ("pushover", _("Pushover")),
                            ("siren", _("Siren")),
                            ("spacealarm", _("Space Alarm")),
                            ("tugboat", _("Tug Boat")),
                            ("updown", _("Up Down (long)")),
                            ("vibrate", _("Vibrate only")),
                        ],
                        default_value="none",
                    ),
                ),
            ],
        )

    # We have to transform because 'add_to_event_context'
    # in modules/events.py can't handle complex data structures
    def _transform_from_pushover_priority(self, params):
        if isinstance(params, tuple):
            return {
                "priority": "2",
                "retry": params[1][0],
                "expire": params[1][1],
                "receipts": params[1][2],
            }
        return params

    def _transform_to_pushover_priority(self, params):
        if isinstance(params, dict):
            return (params["priority"], (params["retry"], params["expire"], params["receipts"]))
        return params
