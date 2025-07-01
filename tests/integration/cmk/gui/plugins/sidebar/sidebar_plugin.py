#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.sidebar import SidebarSnapin, snapin_registry


class SnapinTest(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "test"

    @classmethod
    def title(cls) -> str:
        return "test"

    @classmethod
    def description(cls) -> str:
        return "test"

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    def show(self, config: Config) -> None:
        pass


snapin_registry.register(SnapinTest)
