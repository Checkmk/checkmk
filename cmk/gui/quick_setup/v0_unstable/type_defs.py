#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, MutableSequence
from dataclasses import dataclass
from typing import Any, Literal, NewType

from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId

ActionId = NewType("ActionId", str)
QuickSetupId = NewType("QuickSetupId", str)
StageIndex = NewType("StageIndex", int)
RawFormData = NewType("RawFormData", Mapping[FormSpecId, object])
ParsedFormData = Mapping[FormSpecId, Any]
GeneralStageErrors = MutableSequence[str]


@dataclass(frozen=True)
class ServiceInterest:
    check_plugin_name_pattern: str
    label: str


IconName = Literal[
    "about-checkmk",
    "alert-crit",
    "alert-up",
    "alert-warn",
    "back",
    "cancel",
    "check",
    "checkmark",
    "checkmark-plus",
    "close",
    "continue",
    "crit-problem",
    "cross",
    "drag",
    "edit",
    "folder-blue",
    "help-activated",
    "info",
    "info-circle",
    "insertdate",
    "load-graph",
    "main-help",
    "pending-task",
    "plus",
    "save",
    "save-to-services",
    "search",
    "tree-closed",
]
"""Maps to a related css variable, i.e. --icon-save-to-services."""
