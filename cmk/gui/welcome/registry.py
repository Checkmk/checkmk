#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.web.utils.urls import HTTPVariable


@dataclass
class WelcomeCardUrl:
    id: str
    vars: list[HTTPVariable]
    filename: str


@dataclass
class WelcomeCardCallback:
    id: str
    callback_id: str


@dataclass
class WelcomeCardDynamicUrl:
    """A card whose URL depends on the current configuration.

    make_vars returns None if the card should not be shown right now.
    """

    id: str
    make_vars: Callable[[], list[HTTPVariable] | None]
    filename: str


type WelcomeCard = WelcomeCardUrl | WelcomeCardCallback | WelcomeCardDynamicUrl


class WelcomeCardRegistry(Registry[WelcomeCard]):
    @override
    def plugin_name(self, instance: WelcomeCard) -> str:
        return instance.id


welcome_card_registry = WelcomeCardRegistry()


@dataclass(frozen=True)
class WelcomeFlag:
    """A fact about the site the welcome page adapts to, e.g. whether a relay is configured."""

    id: str
    value: Callable[[], bool]


class WelcomeFlagRegistry(Registry[WelcomeFlag]):
    @override
    def plugin_name(self, instance: WelcomeFlag) -> str:
        return instance.id


welcome_flag_registry = WelcomeFlagRegistry()
