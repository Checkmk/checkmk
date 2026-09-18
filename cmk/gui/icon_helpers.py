#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.shared_typing.main_menu import (
    DefaultIcon,
    EmblemIcon,
    UserIcon,
)
from cmk.shared_typing.main_menu import DynamicIcon as SharedDynamicIcon
from cmk.web.utils.icons import DynamicIcon, IconNames, StaticIcon


def _to_icon_name(name: str) -> IconNames:
    try:
        return IconNames[name.replace("-", "_")]
    except KeyError:
        pass
    try:
        return IconNames(name.replace("_", "-"))
    except ValueError:
        return IconNames.missing


def migrate_to_static_icon(icon: SharedDynamicIcon | None) -> StaticIcon | None:
    if not icon:
        return None

    if isinstance(icon, EmblemIcon):
        return StaticIcon(_to_icon_name(icon.icon.id), emblem=icon.emblem)

    return StaticIcon(_to_icon_name(icon.id))


def migrate_to_dynamic_icon(
    icon: str | StaticIcon | DynamicIcon | SharedDynamicIcon | None,
) -> SharedDynamicIcon | None:
    if not icon:
        return None

    if isinstance(icon, (UserIcon, DefaultIcon, EmblemIcon)):
        return icon

    if isinstance(icon, str):
        return DefaultIcon(id=_to_icon_name(icon))

    if isinstance(icon, StaticIcon):
        default_icon = DefaultIcon(id=icon.icon)
        if icon.emblem:
            return EmblemIcon(icon=default_icon, emblem=icon.emblem)

        return default_icon

    if icon["icon"]:
        default_icon = DefaultIcon(id=_to_icon_name(icon["icon"]))
        if icon["emblem"]:
            return EmblemIcon(icon=default_icon, emblem=icon["emblem"])

        return default_icon

    return None
