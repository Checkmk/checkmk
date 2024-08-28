#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket

from cmk.ccc.site import url_prefix

from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, DEF_VALUE, TextInput, Transform


def notification_macro_help() -> str:
    return _(
        "Here you are allowed to use all macros that are defined in the "
        "notification context.<br>"
        "The most important are:"
        "<ul>"
        "<li><tt>$HOSTNAME$</li>"
        "<li><tt>$SERVICEDESC$</li>"
        "<li><tt>$SERVICESHORTSTATE$</li>"
        "<li><tt>$SERVICEOUTPUT$</li>"
        "<li><tt>$LONGSERVICEOUTPUT$</li>"
        "<li><tt>$SERVICEPERFDATA$</li>"
        "<li><tt>$EVENT_TXT$</li>"
        "</ul>"
    )


def local_site_url() -> str:
    return "http://" + socket.gethostname() + url_prefix() + "check_mk/"


def get_url_prefix_specs(default_choice, default_value=DEF_VALUE):
    return Transform(
        valuespec=CascadingDropdown(
            title=_("URL prefix for links to Checkmk"),
            help=_(
                "If you use <b>Automatic HTTP/s</b>, the URL prefix for host "
                "and service links within the notification is filled "
                "automatically. If you specify an URL prefix here, then "
                "several parts of the notification are armed with hyperlinks "
                "to your Checkmk GUI. In both cases, the recipient of the "
                "notification can directly visit the host or service in "
                "question in Checkmk. Specify an absolute URL including the "
                "<tt>.../check_mk/</tt>."
            ),
            choices=[
                ("automatic_http", _("Automatic HTTP")),
                ("automatic_https", _("Automatic HTTPs")),
                (
                    "manual",
                    _("Specify URL prefix"),
                    TextInput(
                        regex="^(http|https)://.*/check_mk/$",
                        regex_error=_(
                            "The URL must begin with <tt>http</tt> or "
                            "<tt>https</tt> and end with <tt>/check_mk/</tt>."
                        ),
                        size=64,
                        default_value=default_choice,
                    ),
                ),
            ],
            default_value=default_value,
        ),
        to_valuespec=_transform_to_valuespec_html_mail_url_prefix,
        from_valuespec=_transform_from_valuespec_html_mail_url_prefix,
    )


# We have to transform because 'add_to_event_context'
# in modules/events.py can't handle complex data structures
def _transform_from_valuespec_html_mail_url_prefix(p):
    if isinstance(p, tuple):
        return {p[0]: p[1]}
    if p == "automatic_http":
        return {"automatic": "http"}
    if p == "automatic_https":
        return {"automatic": "https"}
    return {"manual": p}


def _transform_to_valuespec_html_mail_url_prefix(p):
    if not isinstance(p, dict):
        return ("manual", p)

    k, v = list(p.items())[0]
    if k == "automatic":
        return f"{k}_{v}"

    return ("manual", v)
