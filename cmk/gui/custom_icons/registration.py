#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.permissions import PermissionRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry

from ._main_menu import MainModuleIcons
from ._modes import register as modes_register


def custom_icons_register(
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    modes_register(mode_registry, permission_registry)
    main_module_registry.register(MainModuleIcons)
