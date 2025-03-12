#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.plugin_registry import Registry

from .base import Layout


class LayoutRegistry(Registry[type[Layout]]):
    @override
    def plugin_name(self, instance: type[Layout]) -> str:
        return instance().ident

    def get_choices(self) -> list[tuple[str, str]]:
        choices = []
        for plugin_class in self.values():
            layout = plugin_class()
            choices.append((layout.ident, layout.title))

        return choices


layout_registry = LayoutRegistry()
