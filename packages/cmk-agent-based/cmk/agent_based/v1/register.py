#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum


class RuleSetType(enum.Enum):
    """Indicate the type of the rule set

    Discovery and host label functions may either use all rules of a rule set matching
    the current host, or the merged rules.
    """

    MERGED = enum.auto()
    ALL = enum.auto()
