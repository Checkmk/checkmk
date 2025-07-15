#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

from cmk.ccc.plugin_registry import Registry

from cmk.gui.config import Config
from cmk.gui.type_defs import Choices

AutocompleterFunc = Callable[[Config, str, dict], Choices]


class AutocompleterRegistry(Registry[AutocompleterFunc]):
    def plugin_name(self, instance):
        return instance._ident

    def register_autocompleter(self, ident: str, func: AutocompleterFunc) -> None:
        if not callable(func):
            raise TypeError()

        # We define the attribute here. for the `plugin_name` method.
        func._ident = ident  # type: ignore[attr-defined]

        self.register(func)


autocompleter_registry = AutocompleterRegistry()
