#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.plugin_registry import Registry

from cmk.gui.config import active_config

from ._base import UserAttribute
from ._custom_attributes import config_based_custom_user_attributes


class UserAttributeRegistry(Registry[type[UserAttribute]]):
    """The management object for all available user attributes.
    Have a look at the base class for details."""

    def plugin_name(self, instance):
        return instance.name()


user_attribute_registry = UserAttributeRegistry()


def all_user_attributes() -> list[tuple[str, type[UserAttribute]]]:
    return [
        *user_attribute_registry.items(),
        *config_based_custom_user_attributes(active_config.wato_user_attrs),
    ]


def get_user_attributes() -> list[tuple[str, UserAttribute]]:
    return [(name, attribute_class()) for name, attribute_class in all_user_attributes()]


def get_user_attributes_by_topic() -> dict[str, list[tuple[str, UserAttribute]]]:
    topics: dict[str, list[tuple[str, UserAttribute]]] = {}
    for name, attr_class in all_user_attributes():
        topic = attr_class().topic()
        topics.setdefault(topic, []).append((name, attr_class()))

    return topics
