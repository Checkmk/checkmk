#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from cmk.ccc.user import UserId

from cmk.rulesets.v1 import form_specs, Help, Label, Title


class LegacyFilter(NamedTuple):
    only_contacts: bool
    only_automation: bool


@dataclass(frozen=True, kw_only=True)
class UserSelectionFilter(Enum):
    ALL = "all"
    CONTACTS = "contact"
    AUTOMATION = "automation"

    def to_legacy(self) -> LegacyFilter:
        if self is UserSelectionFilter.ALL:
            return LegacyFilter(
                only_contacts=False,
                only_automation=False,
            )
        if self is UserSelectionFilter.CONTACTS:
            return LegacyFilter(
                only_contacts=True,
                only_automation=False,
            )
        if self is UserSelectionFilter.AUTOMATION:
            return LegacyFilter(
                only_contacts=False,
                only_automation=True,
            )
        raise NotImplementedError("Got undefined filter value")


@dataclass(frozen=True, kw_only=True)
class UserSelection(form_specs.FormSpec[UserId]):
    """Keep in mind that the parameter_form may not return None as parameter
    None is already reserved by the OptionalChoice itself to represent
    the absence of a choice.

    With the negate flag set to True, the meaning of the checkbox is inverted.
    So if the checkbox is checked, the parameter will be set to None, anything else
    means unchecked
    """

    title: Title | None = None
    help_text: Help | None = None
    migrate: Callable[[object], UserId] | None = None
    custom_validate: Sequence[Callable[[UserId | None], object]] | None = None

    filter: UserSelectionFilter = UserSelectionFilter.ALL
    label: Label | None = None
