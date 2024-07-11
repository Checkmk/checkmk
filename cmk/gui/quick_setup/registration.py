#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.main_menu import MainModuleRegistry

from . import _modes


def register(
    main_module_registry: MainModuleRegistry,
) -> None:
    _modes.register(main_module_registry)
