#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.type_defs import HTTPVariables


@dataclass
class WelcomeUrl:
    id: str
    vars: HTTPVariables
    filename: str


class WelcomeUrlRegistry(Registry[WelcomeUrl]):
    @override
    def plugin_name(self, instance: WelcomeUrl) -> str:
        return instance.id


welcome_url_registry = WelcomeUrlRegistry()
