#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import Widget

CallableValidator = Callable[[QuickSetupId, StageIndex, ParsedFormData], GeneralStageErrors]
CallableRecap = Callable[[QuickSetupId, StageIndex, ParsedFormData], Sequence[Widget]]
CallableSaveAction = Callable[[ParsedFormData], str]
WidgetConfigurator = Callable[[], Sequence[Widget]]


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
    stages: Sequence[QuickSetupStage]
    button_complete_label: str
    save_action: CallableSaveAction | None = None
