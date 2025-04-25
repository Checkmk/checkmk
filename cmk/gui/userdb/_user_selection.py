#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any

from cmk.ccc.user import UserId

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    DEF_VALUE,
    DropdownChoice,
    Transform,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
)

from .store import load_users


def UserSelection(
    only_contacts: bool = False,
    only_automation: bool = False,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[UserId] = DEF_VALUE,
) -> Transform[UserId | None]:
    # this has been ported to formspec be carfule about changes!
    return Transform(
        valuespec=_UserSelection(
            only_contacts=only_contacts,
            only_automation=only_automation,
            title=title,
            help=help,
            default_value=default_value,
        ),
        to_valuespec=lambda raw_str: None if raw_str is None else UserId(raw_str),
        from_valuespec=lambda uid: None if uid is None else str(uid),
    )


class _UserSelection(DropdownChoice[UserId]):
    """Dropdown for choosing a multisite user"""

    def __init__(
        self,
        only_contacts: bool = False,
        only_automation: bool = False,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[UserId] = DEF_VALUE,
    ) -> None:
        super().__init__(
            choices=generate_wato_users_elements_function(
                only_contacts=only_contacts, only_automation=only_automation
            ),
            invalid_choice="complain",
            title=title,
            empty_text=_("No valid users available"),
            help=help,
            default_value=default_value,
        )

    def value_to_html(self, value: Any) -> ValueSpecText:
        return str(super().value_to_html(value)).rsplit(" - ", 1)[-1]


def generate_wato_users_elements_function(
    only_contacts: bool = False,
    only_automation: bool = False,
) -> Callable[[], list[tuple[UserId | None, str]]]:
    def get_wato_users() -> list[tuple[UserId | None, str]]:
        users = load_users()
        elements: list[tuple[UserId | None, str]] = sorted(
            (name, "{} - {}".format(name, us.get("alias", name)))
            for (name, us) in users.items()
            if (not only_contacts or us.get("contactgroups"))
            and (
                not only_automation
                or (us.get("store_automation_secret") and us.get("is_automation_user"))
            )
        )
        return elements

    return get_wato_users
