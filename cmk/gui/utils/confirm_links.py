#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Links that ask the user for confirmation before following through."""

import json

from cmk.gui.i18n import _
from cmk.gui.utils.urls import quote_plus
from cmk.web.utils.escaping import escape_text


def make_confirm_link(
    *,
    url: str,
    title: str,
    suffix: str | None = None,
    message: str | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
) -> str:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else _("Yes"),
        cancel_button=cancel_button if cancel_button else _("No"),
        message=message,
    )


def make_confirm_delete_link(
    *,
    url: str,
    title: str,
    suffix: str | None = None,
    message: str | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
    warning: bool = False,
    post_confirm_waiting_text: str | None = None,
) -> str:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else _("Delete"),
        cancel_button=cancel_button if cancel_button else _("Cancel"),
        message=message,
        icon="warning" if warning else "question",
        custom_class_options={
            "confirmButton": "confirm_warning" if warning else "confirm_question",
            "icon": "confirm_icon" + (" confirm_warning" if warning else " confirm_question"),
        },
        post_confirm_waiting_text=post_confirm_waiting_text,
    )


def _make_customized_confirm_link(
    *,
    url: str,
    title: str,
    confirm_button: str,
    cancel_button: str,
    message: str | None = None,
    icon: str | None = None,
    custom_class_options: dict[str, str] | None = None,
    post_confirm_waiting_text: str | None = None,
) -> str:
    return "javascript:cmk.forms.confirm_link({}, {}, {}, {}),cmk.popup_menu.close_popup()".format(
        json.dumps(quote_plus(url)),
        json.dumps(escape_text(message, escape_links=True)),
        json.dumps(
            {
                "title": escape_text(title, escape_links=True),
                "confirmButtonText": confirm_button,
                "cancelButtonText": cancel_button,
                "icon": icon if icon else "question",
                "customClass": custom_class_options if custom_class_options else {},
            }
        ),
        json.dumps(post_confirm_waiting_text),
    )


def get_confirm_link_title(
    title: str | None = None,
    suffix: str | None = None,
) -> str:
    if title is None:
        return ""
    if title and suffix:
        return title + f" - {suffix}?"
    return title + "?"
