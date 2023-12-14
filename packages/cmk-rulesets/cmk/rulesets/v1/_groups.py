#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import auto, Enum

from cmk.rulesets.v1._localize import Localizable


class Topic(Enum):
    APPLICATIONS = auto()
    OPERATING_SYSTEM = auto()
    VIRTUALIZATION = auto()
    GENERAL = auto()


@dataclass(frozen=True)
class CustomTopic:
    """
    Args:
        title: human-readable title of this group
    """

    title: Localizable
