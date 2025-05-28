#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import override

from cmk.ccc.plugin_registry import Registry

from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup


class QuickSetupRegistry(Registry[QuickSetup]):
    @override
    def plugin_name(self, instance: QuickSetup) -> str:
        return str(instance.id)

    @override
    def register(self, instance: QuickSetup) -> QuickSetup:
        # TODO: reintroduce Formspec id validation after dynamic stage discussion
        #  SuperUser context will be required as registration happens outside user request context
        return super().register(instance)


quick_setup_registry = QuickSetupRegistry()
