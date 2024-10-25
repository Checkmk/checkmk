#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import Widget


class QuickSetupActionMode(StrEnum):
    SAVE = "save"
    EDIT = "edit"


CallableValidator = Callable[[QuickSetupId, StageIndex, ParsedFormData], GeneralStageErrors]
CallableRecap = Callable[[QuickSetupId, StageIndex, ParsedFormData], Sequence[Widget]]
CallableAction = Callable[[ParsedFormData, QuickSetupActionMode, str | None], str]
WidgetConfigurator = Callable[[], Sequence[Widget]]


@dataclass(frozen=True)
class QuickSetupAction:
    id: str
    label: str
    action: CallableAction


@dataclass(frozen=True)
class QuickSetupStage:
    title: str
    configure_components: WidgetConfigurator | Sequence[Widget]
    custom_validators: Iterable[CallableValidator]
    recap: Iterable[CallableRecap]
    button_label: str
    sub_title: str | None = None


@dataclass(frozen=True)
class QuickSetup:
    title: str
    id: QuickSetupId
    stages: Sequence[Callable[[], QuickSetupStage]]
    actions: Sequence[QuickSetupAction]
    load_data: Callable[[str], ParsedFormData | None] = lambda _: None
