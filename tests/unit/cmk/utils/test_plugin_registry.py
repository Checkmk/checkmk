#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.ccc.plugin_registry


class Plugin:
    pass


class PluginRegistry(cmk.ccc.plugin_registry.Registry[type[Plugin]]):
    def plugin_name(self, instance):
        return instance.__name__


@pytest.fixture(scope="module")
def basic_registry():
    registry = PluginRegistry()
    registry.register(Plugin)
    return registry


def test_initialization() -> None:
    registry = PluginRegistry()
    assert not list(registry.items())


def test_decorator_registration() -> None:
    registry = PluginRegistry()
    assert not list(registry.items())

    @registry.register
    class DecoratedPlugin(Plugin):
        pass

    assert registry.get("DecoratedPlugin") == DecoratedPlugin


def test_method_registration() -> None:
    registry = PluginRegistry()
    assert not list(registry.items())

    class MethodRegisteredPlugin(Plugin):
        pass

    registry.register(MethodRegisteredPlugin)
    assert registry.get("MethodRegisteredPlugin") == MethodRegisteredPlugin


def test_contains(basic_registry: PluginRegistry) -> None:
    assert "bla" not in basic_registry
    assert "Plugin" in basic_registry


def test_delitem(basic_registry: PluginRegistry) -> None:
    with pytest.raises(KeyError):
        basic_registry.unregister("bla")

    @basic_registry.register
    class DelPlugin(Plugin):
        pass

    basic_registry.unregister("DelPlugin")


def test_clear() -> None:
    registry = PluginRegistry()
    registry.register(Plugin)
    assert "Plugin" in registry

    registry.clear()
    assert "Plugin" not in registry


def test_getitem(basic_registry: PluginRegistry) -> None:
    with pytest.raises(KeyError):
        _unused = basic_registry["bla"]

    assert basic_registry["Plugin"] == Plugin


def test_values(basic_registry: PluginRegistry) -> None:
    assert list(basic_registry.values()) == [Plugin]


def test_items(basic_registry: PluginRegistry) -> None:
    assert list(basic_registry.items()) == [("Plugin", Plugin)]


def test_keys(basic_registry: PluginRegistry) -> None:
    assert list(basic_registry.keys()) == ["Plugin"]


def test_get(basic_registry: PluginRegistry) -> None:
    assert basic_registry.get("bla") is None
    assert basic_registry.get("bla", "blub") == "blub"

    assert basic_registry.get("Plugin") == Plugin


class InstanceRegistry(cmk.ccc.plugin_registry.Registry[Plugin]):
    def plugin_name(self, instance):
        return instance.__class__.__name__
