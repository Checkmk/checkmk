#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Links that ask the user for confirmation before following through."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from cmk.web.utils.escaping import escape_text
from cmk.web.utils.html import HTML


@dataclass(frozen=True, kw_only=True)
class ConfirmLink:
    """Asks for confirmation and then POSTs to ``url``

    Rendered as a click action by the HTML helpers which accept it."""

    url: str
    message: str
    options: Mapping[str, object]
    post_confirm_waiting_text: str | None

    def arguments(self) -> dict[str, object]:
        return {
            "url": self.url,
            "message": self.message,
            "options": dict(self.options),
            "post_confirm_waiting_text": self.post_confirm_waiting_text,
        }


def make_confirm_link(
    *,
    url: str,
    title: str,
    i18n: Callable[[str], str],
    suffix: str | None = None,
    message: str | HTML | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
) -> ConfirmLink:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else i18n("Yes"),
        cancel_button=cancel_button if cancel_button else i18n("No"),
        message=message,
    )


def make_confirm_delete_link(
    *,
    url: str,
    title: str,
    i18n: Callable[[str], str],
    suffix: str | None = None,
    message: str | HTML | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
    warning: bool = False,
    post_confirm_waiting_text: str | None = None,
) -> ConfirmLink:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else i18n("Delete"),
        cancel_button=cancel_button if cancel_button else i18n("Cancel"),
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
    message: str | HTML | None = None,
    icon: str | None = None,
    custom_class_options: dict[str, str] | None = None,
    post_confirm_waiting_text: str | None = None,
) -> ConfirmLink:
    """Build the dialog link. A ``str`` message keeps the simple formatting tags that
    ``escape_text`` allows and loses only its links; an ``HTML`` one is written as it is, so
    whoever builds it owns its escaping."""
    return ConfirmLink(
        url=url,
        message=escape_text(message, escape_links=True),
        options={
            "title": escape_text(title, escape_links=True),
            "confirmButtonText": confirm_button,
            "cancelButtonText": cancel_button,
            "icon": icon if icon else "question",
            "customClass": custom_class_options if custom_class_options else {},
        },
        post_confirm_waiting_text=post_confirm_waiting_text,
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
