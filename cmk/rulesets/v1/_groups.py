#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import auto, Enum

from cmk.rulesets.v1._localize import Localizable


class RuleSpecMainGroup(Enum):
    MONITORING_CONFIGURATION = auto()


class RuleSpecSubGroup(Enum):
    CHECK_PARAMETERS_APPLICATIONS = auto()


@dataclass(frozen=True)
class RuleSpecCustomMainGroup:
    """Main topic to group sub-groups of rulespecs further together

    Args:
        name: identifier of this group
        title: human-readable title of this group
        help_text: description of the content of this group
    """

    name: str
    title: Localizable
    help_text: Localizable


@dataclass(frozen=True)
class RuleSpecCustomSubGroup:
    """Group rulespecs for a similar purpose together

    Args:
        main_group: topic to group this and other groups with the same main-group under
        name: identifier of this group
        title: human-readable title of this group
    """

    main_group: RuleSpecMainGroup | RuleSpecCustomMainGroup
    name: str  # TODO: previously: getter: combination of main group name and sub group name
    title: Localizable
