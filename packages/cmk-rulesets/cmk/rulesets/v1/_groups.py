#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import auto, Enum

from cmk.rulesets.v1._localize import Localizable


class Functionality(Enum):
    ENFORCED_SERVICES = auto()
    MONITORING_CONFIGURATION = auto()


class Topic(Enum):
    APPLICATIONS = auto()
    OPERATING_SYSTEM = auto()
    VIRTUALIZATION = auto()


@dataclass(frozen=True)
class CustomFunctionality:
    """
    Args:
        title: human-readable title of this group
        help_text: description of the content of this functionality
    """

    title: Localizable
    help_text: Localizable


@dataclass(frozen=True)
class CustomTopic:
    """
    Args:
        title: human-readable title of this group
    """

    title: Localizable
