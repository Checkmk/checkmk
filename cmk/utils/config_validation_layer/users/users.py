#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal

from pydantic import BaseModel

from cmk.utils.config_validation_layer.type_defs import OMITTED_FIELD

TEMPERATURE = Literal["celsius", "fahrenheit"]

SHOW_MODE = Literal["default_show_less", "default_show_more", "enforce_show_more"]


class User(BaseModel):
    username: str
    alias: str
    connector: str = OMITTED_FIELD
    locked: bool = OMITTED_FIELD
    roles: list[str] = OMITTED_FIELD
    temperature_unit: TEMPERATURE | None = OMITTED_FIELD
    force_authuser: bool = OMITTED_FIELD
    nav_hide_icons_title: Literal["hide"] | None = OMITTED_FIELD
    icons_per_item: Literal["entry"] | None = OMITTED_FIELD
    show_mode: SHOW_MODE | None = OMITTED_FIELD
    automation_secret: str = OMITTED_FIELD
    language: str = OMITTED_FIELD


def validate_users(users: dict[str, Any]) -> None:
    for name, user in users.items():
        validate_user(name, user)


def validate_user(name: str, user: dict) -> None:
    User(username=name, **user)
