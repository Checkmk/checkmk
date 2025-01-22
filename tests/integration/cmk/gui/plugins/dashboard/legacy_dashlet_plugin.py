#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Initialize the UI environment to make loading of the dashlet possible.
from cmk.gui import main_modules

# Needs to come before the following import (adds some compatibility names)
main_modules.load_plugins()

from cmk.gui.plugins.dashboard import (  # type: ignore[attr-defined] # pylint: disable=no-name-in-module # noqa: E402
    Dashlet,
    dashlet_registry,
)


@dashlet_registry.register
class TestDashlet(Dashlet):  # type: ignore[misc]
    @classmethod
    def type_name(cls):
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def description(cls):
        return "test"

    @classmethod
    def sort_index(cls) -> int:
        return 0

    @classmethod
    def is_selectable(cls) -> bool:
        return False

    def show(self):
        pass
