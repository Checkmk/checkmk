#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.plugin_registry import Registry
from cmk.gui.watolib.mode_permissions import mode_permissions_ensurance_registry

from ._base import WatoMode


class ModeRegistry(Registry[type[WatoMode]]):
    def plugin_name(self, instance: type[WatoMode]) -> str:
        return instance.name()

    def register(self, instance: type[WatoMode]) -> type[WatoMode]:
        super().register(instance)
        mode_permissions_ensurance_registry.register(instance)
        return instance


mode_registry = ModeRegistry()
