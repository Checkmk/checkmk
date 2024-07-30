#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Iterator, Sequence

from cmk.gui.quick_setup.v0_unstable.definitions import UniqueFormSpecIDStr
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecWrapper,
    ListOfWidgets,
    Widget,
)

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry


class MissingRequiredFormSpecError(MKGeneralException):
    def __init__(self):
        super().__init__(f"Required formspec wrapper with id '{UniqueFormSpecIDStr}' is missing.")


def _flatten_formspec_wrappers(components: Sequence[Widget]) -> Iterator[FormSpecWrapper]:
    for component in components:
        if isinstance(component, (ListOfWidgets, Collapsible)):
            yield from iter(_flatten_formspec_wrappers(component.items))

        if isinstance(component, FormSpecWrapper):
            yield component


class QuickSetupRegistry(Registry[QuickSetup]):
    def plugin_name(self, instance: QuickSetup) -> str:
        return str(instance.id)

    def _check_for_required_formspec(self, instance: QuickSetup) -> None:
        if UniqueFormSpecIDStr not in [
            wrapper.id
            for stage in instance.stages
            for wrapper in _flatten_formspec_wrappers(stage.configure_components)
        ]:
            raise MissingRequiredFormSpecError()

    def register(self, instance: QuickSetup) -> QuickSetup:
        self._check_for_required_formspec(instance)
        return super().register(instance)


quick_setup_registry = QuickSetupRegistry()
