#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.ms_teams_constants import (
    ms_teams_tmpl_host_details,
    ms_teams_tmpl_host_summary,
    ms_teams_tmpl_host_title,
    ms_teams_tmpl_svc_details,
    ms_teams_tmpl_svc_summary,
    ms_teams_tmpl_svc_title,
)

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    HTTPUrl,
    TextAreaUnicode,
    TextInput,
)
from cmk.gui.wato import HTTPProxyReference
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url, notification_macro_help


class NotificationParameterMsTeams(NotificationParameter):
    @property
    def ident(self) -> str:
        return "msteams"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            elements=[
                (
                    "webhook_url",
                    CascadingDropdown(
                        title=_("Webhook URL"),
                        help=_(
                            "Create a workflow 'Post to a channel when a "
                            "webhook request is received' for a channel in MS "
                            "Teams and use the generated webook URL.<br><br>"
                            "This URL can also be collected from the Password "
                            "Store from Checkmk."
                        ),
                        choices=[
                            (
                                "webhook_url",
                                _("Webhook URL"),
                                HTTPUrl(size=80, allow_empty=False),
                            ),
                            (
                                "store",
                                _("URL from password store"),
                                DropdownChoice(
                                    sorted=True,
                                    choices=passwordstore_choices,
                                ),
                            ),
                        ],
                        sorted=False,
                    ),
                ),
                ("proxy_url", HTTPProxyReference()),
                ("url_prefix", get_url_prefix_specs(local_site_url)),
                (
                    "host_title",
                    TextInput(
                        title=_("Title for host notifications"),
                        help=notification_macro_help(),
                        default_value=ms_teams_tmpl_host_title(),
                        size=64,
                    ),
                ),
                (
                    "service_title",
                    TextInput(
                        title=_("Title for service notifications"),
                        help=notification_macro_help(),
                        default_value=ms_teams_tmpl_svc_title(),
                        size=64,
                    ),
                ),
                (
                    "host_summary",
                    TextInput(
                        title=_("Summary for host notifications"),
                        help=notification_macro_help(),
                        default_value=ms_teams_tmpl_host_summary(),
                        size=64,
                    ),
                ),
                (
                    "service_summary",
                    TextInput(
                        title=_("Summary for service notifications"),
                        help=notification_macro_help(),
                        default_value=ms_teams_tmpl_svc_summary(),
                        size=64,
                    ),
                ),
                (
                    "host_details",
                    TextAreaUnicode(
                        title=_("Details for host notifications"),
                        help=notification_macro_help(),
                        rows=9,
                        cols=58,
                        monospaced=True,
                        default_value=ms_teams_tmpl_host_details(),
                    ),
                ),
                (
                    "service_details",
                    TextAreaUnicode(
                        title=_("Details for service notifications"),
                        help=notification_macro_help(),
                        rows=11,
                        cols=58,
                        monospaced=True,
                        default_value=ms_teams_tmpl_svc_details(),
                    ),
                ),
                (
                    "affected_host_groups",
                    FixedValue(
                        value=True,
                        title=_("Show affected host groups"),
                        totext=_("Show affected host groups"),
                        help=_("Show affected host groups in the created message."),
                    ),
                ),
            ],
        )
