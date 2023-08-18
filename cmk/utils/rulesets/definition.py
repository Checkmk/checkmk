#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum


class RuleGroupType(enum.Enum):
    ACTIVE_CHECKS = "active_checks"


class RuleGroup:
    @staticmethod
    def ActiveChecks(name: str | None) -> str:
        return f"{RuleGroupType.ACTIVE_CHECKS.value}:{name}"
