#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Names are made available dynamically
from cmk.gui.plugins.sidebar.utils import (  # type: ignore[attr-defined]
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class CurrentTime(SidebarSnapin):  # type: ignore[misc]
    @staticmethod
    def type_name():
        return "test"

    @classmethod
    def title(cls):
        return "test"

    @classmethod
    def description(cls):
        return "test"

    @classmethod
    def refresh_regularly(cls):
        return True

    def show(self, config):
        pass
