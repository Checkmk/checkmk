#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Type

# pylint: disable=redefined-outer-name
import pytest

import cmk.utils.plugin_registry


class Plugin:
    pass


class PluginRegistry(cmk.utils.plugin_registry.Registry[Type[Plugin]]):
    def plugin_name(self, instance):
        return instance.__name__


@pytest.fixture(scope="module")
def basic_registry():
    registry = PluginRegistry()
    registry.register(Plugin)
    return registry


def test_initialization() -> None:
    registry = PluginRegistry()
    assert list(registry.items()) == []


def test_decorator_registration() -> None:
    registry = PluginRegistry()
    assert list(registry.items()) == []

    @registry.register
    class DecoratedPlugin(Plugin):
        pass

    assert registry.get("DecoratedPlugin") == DecoratedPlugin


def test_method_registration() -> None:
    registry = PluginRegistry()
    assert list(registry.items()) == []

    class MethodRegisteredPlugin(Plugin):
        pass

    registry.register(MethodRegisteredPlugin)
    assert registry.get("MethodRegisteredPlugin") == MethodRegisteredPlugin


def test_contains(basic_registry) -> None:
    assert "bla" not in basic_registry
    assert "Plugin" in basic_registry


def test_delitem(basic_registry) -> None:
    with pytest.raises(KeyError):
        basic_registry.unregister("bla")

    @basic_registry.register
    class DelPlugin(Plugin):  # pylint: disable=unused-variable
        pass

    basic_registry.unregister("DelPlugin")


def test_getitem(basic_registry) -> None:
    with pytest.raises(KeyError):
        _unused = basic_registry["bla"]  # noqa: F841

    assert basic_registry["Plugin"] == Plugin


def test_values(basic_registry) -> None:
    assert list(basic_registry.values()) == [Plugin]


def test_items(basic_registry) -> None:
    assert list(basic_registry.items()) == [("Plugin", Plugin)]


def test_keys(basic_registry) -> None:
    assert list(basic_registry.keys()) == ["Plugin"]


def test_get(basic_registry) -> None:
    assert basic_registry.get("bla") is None
    assert basic_registry.get("bla", "blub") == "blub"

    assert basic_registry.get("Plugin") == Plugin


class InstanceRegistry(cmk.utils.plugin_registry.Registry[Plugin]):
    def plugin_name(self, instance):
        return instance.__class__.__name__


def test_decorate_classes_for_instance_registry() -> None:
    registry = InstanceRegistry()
    assert list(registry.items()) == []

    @registry.register_instance
    class DecoratedPlugin(Plugin):
        pass

    assert isinstance(registry.get("DecoratedPlugin"), DecoratedPlugin)
