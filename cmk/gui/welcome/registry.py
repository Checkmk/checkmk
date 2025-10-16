#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.type_defs import HTTPVariables


@dataclass
class WelcomeCardUrl:
    id: str
    vars: HTTPVariables
    filename: str


@dataclass
class WelcomeCardCallback:
    id: str
    callback_id: str


class WelcomeCardRegistry(Registry[WelcomeCardUrl | WelcomeCardCallback]):
    @override
    def plugin_name(self, instance: WelcomeCardUrl | WelcomeCardCallback) -> str:
        return instance.id


welcome_card_registry = WelcomeCardRegistry()
