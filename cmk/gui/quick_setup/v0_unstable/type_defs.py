#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, MutableSequence
from dataclasses import dataclass
from typing import Any, NewType

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
