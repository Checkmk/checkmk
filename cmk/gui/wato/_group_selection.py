#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import Any

from cmk.gui.groups import GroupSpecs
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import ChoiceText
from cmk.gui.valuespec import ElementSelection
from cmk.gui.watolib.groups_io import (
    load_contact_group_information,
    load_host_group_information,
    load_service_group_information,
)


# TODO: Refactor this and all other children of ElementSelection() to base on
#       DropdownChoice(). Then remove ElementSelection()
class _GroupSelection(ElementSelection):
    def __init__(
        self,
        what: str,
        choices: Callable[[], Sequence[tuple[str, str]]],
        no_selection: ChoiceText | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault(
            "empty_text",
            _(
                "You have not defined any %s group yet. Please "
                '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.'
            )
            % (what, what),
        )
        super().__init__(**kwargs)
        self._what = what
        self._choices = choices
        self._no_selection = no_selection

    def get_elements(self):
        elements = list(self._choices())
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(("", self._no_selection))
        return dict(elements)


def ContactGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single contact group"""
    return _GroupSelection("contact", choices=sorted_contact_group_choices, **kwargs)


def ServiceGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single service group"""
    return _GroupSelection("service", choices=sorted_service_group_choices, **kwargs)


def HostGroupSelection(**kwargs: Any) -> ElementSelection:
    """Select a single host group"""
    return _GroupSelection("host", choices=sorted_host_group_choices, **kwargs)


@request_memoize()
def sorted_contact_group_choices() -> Sequence[tuple[str, str]]:
    return _group_choices(load_contact_group_information())


@request_memoize()
def sorted_service_group_choices() -> Sequence[tuple[str, str]]:
    return _group_choices(load_service_group_information())


@request_memoize()
def sorted_host_group_choices() -> Sequence[tuple[str, str]]:
    return _group_choices(load_host_group_information())


def _group_choices(group_information: GroupSpecs) -> Sequence[tuple[str, str]]:
    return sorted(
        [(k, t["alias"] and t["alias"] or k) for (k, t) in group_information.items()],
        key=lambda x: x[1].lower(),
    )
