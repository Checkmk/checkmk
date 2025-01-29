#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Polyfactory has a limitation on more specific Callables, so we override the original dataclasses
to have a more generic type definition for fields which involve those
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from polyfactory.factories.dataclass_factory import DataclassFactory

from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetup,
    QuickSetupAction,
    QuickSetupStage,
    QuickSetupStageAction,
)


@dataclass(frozen=True)
class StageActionForTest(QuickSetupStageAction):
    recap: Sequence
    custom_validators: Sequence


@dataclass(frozen=True)
class QuickSetupStageForTest(QuickSetupStage):
    configure_components: Sequence


@dataclass(frozen=True)
class QuickSetupActionForTest(QuickSetupAction):
    action: Callable
    custom_validators: Sequence[Callable]


@dataclass(frozen=True)
class QuickSetupForTest(QuickSetup):
    stages: Sequence[Callable]
    actions: Sequence[QuickSetupActionForTest]
    load_data: Callable


class QuickSetupFactory(DataclassFactory):
    __model__ = QuickSetupForTest


class QuickSetupStageFactory(DataclassFactory):
    __model__ = QuickSetupStageForTest
