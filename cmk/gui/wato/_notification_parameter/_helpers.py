#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Any

from cmk.ccc.site import url_prefix

from cmk.gui.form_specs.private.dictionary_extended import DictGroupExtended
from cmk.gui.i18n import _

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    FieldSize,
    FixedValue,
    String,
)
from cmk.rulesets.v1.form_specs.validators import Url, UrlProtocol
from cmk.shared_typing.vue_formspec_components import DictionaryGroupLayout


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


# TODO: remove this and replace with the above function, once all callsites are migrated
def notification_macro_help_fs() -> Help:
    return Help(
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


def _get_url_prefix_setting(
    is_cse: bool = False, default_value: str = "automatic_https", group_title: str | None = None
) -> DictElement[Any]:
    return DictElement(
        group=DictGroupExtended(
            title=Title(group_title) if group_title else None,  # pylint: disable=localization-of-non-literal-string
            layout=DictionaryGroupLayout.vertical,
        ),
        parameter_form=CascadingSingleChoice(
            title=Title("URL prefix for links to Checkmk"),
            help_text=Help(
                "If you use <b>Automatic HTTP/s</b>, the URL prefix for "
                "host and service links within the notification is filled "
                "automatically. If you specify an URL prefix here, then "
                "several parts of the notification are armed with hyperlinks "
                "to your Checkmk GUI. In both cases, the recipient of the "
                "notification can directly visit the host or service in "
                "question in Checkmk. Specify an absolute URL including the "
                "<tt>.../check_mk/</tt>."
            ),
            elements=[
                CascadingSingleChoiceElement(
                    name="automatic_http",
                    title=Title("Automatic HTTP"),
                    parameter_form=FixedValue(
                        value=None,
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="automatic_https",
                    title=Title("Automatic HTTPs"),
                    parameter_form=FixedValue(
                        value=None,
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="manual",
                    title=Title("Specify URL prefix"),
                    parameter_form=String(
                        prefill=DefaultValue(local_site_url()),
                        custom_validate=[Url([UrlProtocol.HTTP, UrlProtocol.HTTPS])],
                        field_size=FieldSize.LARGE,
                    ),
                ),
            ],
            migrate=_migrate_url_prefix,
            prefill=DefaultValue(default_value),
        ),
        render_only=is_cse,
    )


def _migrate_url_prefix(p: object) -> tuple[str, str | None]:
    if isinstance(p, tuple):
        return p

    if isinstance(p, str):
        return ("manual", p)

    if isinstance(p, dict):
        for key, value in p.items():
            if key == "manual":
                return (key, value)
            return (f"{key}_{value}", None)

    raise ValueError(f"Invalid format for URL prefix: {p}")
