#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.plugin_registry import Registry

from ._base import UserAttribute


class UserAttributeRegistry(Registry[type[UserAttribute]]):
    """The management object for all available user attributes.
    Have a look at the base class for details."""

    def plugin_name(self, instance):
        return instance.name()


user_attribute_registry = UserAttributeRegistry()


def get_user_attributes() -> list[tuple[str, UserAttribute]]:
    return [(name, attribute_class()) for name, attribute_class in user_attribute_registry.items()]


def get_user_attributes_by_topic() -> dict[str, list[tuple[str, UserAttribute]]]:
    topics: dict[str, list[tuple[str, UserAttribute]]] = {}
    for name, attr_class in user_attribute_registry.items():
        topic = attr_class().topic()
        topics.setdefault(topic, []).append((name, attr_class()))

    return topics
