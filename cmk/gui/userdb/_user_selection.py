#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import Any

from cmk.utils.user import UserId

from cmk.gui.valuespec import (
    DEF_VALUE,
    DropdownChoice,
    Transform,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
)

from .store import load_users


def UserSelection(  # pylint: disable=redefined-builtin
    only_contacts: bool = False,
    only_automation: bool = False,
    none: str | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[UserId] = DEF_VALUE,
) -> Transform[UserId | None]:
    return Transform(
        valuespec=_UserSelection(
            only_contacts=only_contacts,
            only_automation=only_automation,
            none=none,
            title=title,
            help=help,
            default_value=default_value,
        ),
        to_valuespec=lambda raw_str: None if raw_str is None else UserId(raw_str),
        from_valuespec=lambda uid: None if uid is None else str(uid),
    )


class _UserSelection(DropdownChoice[UserId]):
    """Dropdown for choosing a multisite user"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        only_contacts: bool = False,
        only_automation: bool = False,
        none: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[UserId] = DEF_VALUE,
    ) -> None:
        super().__init__(
            choices=self._generate_wato_users_elements_function(
                none, only_contacts=only_contacts, only_automation=only_automation
            ),
            invalid_choice="complain",
            title=title,
            help=help,
            default_value=default_value,
        )

    def _generate_wato_users_elements_function(
        self,
        none_value: str | None,
        only_contacts: bool = False,
        only_automation: bool = False,
    ) -> Callable[[], list[tuple[UserId | None, str]]]:
        def get_wato_users(nv: str | None) -> list[tuple[UserId | None, str]]:
            users = load_users()
            elements: list[tuple[UserId | None, str]] = sorted(
                (name, "{} - {}".format(name, us.get("alias", name)))
                for (name, us) in users.items()
                if (not only_contacts or us.get("contactgroups"))
                and (not only_automation or us.get("is_automation_user"))
            )
            if nv is not None:
                elements.insert(0, (None, nv))
            return elements

        return lambda: get_wato_users(none_value)

    def value_to_html(self, value: Any) -> ValueSpecText:
        return str(super().value_to_html(value)).rsplit(" - ", 1)[-1]
