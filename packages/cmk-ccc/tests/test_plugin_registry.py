#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import pytest

import cmk.ccc.plugin_registry


class Plugin:
    pass


class PluginRegistry(cmk.ccc.plugin_registry.Registry[type[Plugin]]):
    @override
    def plugin_name(self, instance: type[Plugin]) -> str:
        return instance.__name__


def _registry_with_plugin() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(Plugin)
    return registry


def test_new_registry_is_empty() -> None:
    assert not list(PluginRegistry().items())


def test_registered_class_is_found_by_its_plugin_name() -> None:
    registry = PluginRegistry()

    registry.register(Plugin)

    assert registry["Plugin"] is Plugin


def test_register_works_as_class_decorator() -> None:
    registry = PluginRegistry()

    @registry.register
    class DecoratedPlugin(Plugin):
        pass

    assert registry["DecoratedPlugin"] is DecoratedPlugin


def test_looking_up_an_unknown_name_raises_key_error() -> None:
    registry = _registry_with_plugin()

    with pytest.raises(KeyError):
        _ = registry["bla"]


def test_registry_contains_registered_name() -> None:
    assert "Plugin" in _registry_with_plugin()


def test_registry_does_not_contain_unknown_name() -> None:
    assert "bla" not in _registry_with_plugin()


def test_unregistered_name_is_gone() -> None:
    registry = _registry_with_plugin()

    registry.unregister("Plugin")

    assert "Plugin" not in registry


def test_unregistering_an_unknown_name_raises_key_error() -> None:
    registry = _registry_with_plugin()

    with pytest.raises(KeyError):
        registry.unregister("bla")


def test_clear_removes_all_registrations() -> None:
    registry = _registry_with_plugin()

    registry.clear()

    assert not list(registry.items())


def test_values_are_the_registered_objects() -> None:
    assert list(_registry_with_plugin().values()) == [Plugin]


def test_items_pair_plugin_names_with_registered_objects() -> None:
    assert list(_registry_with_plugin().items()) == [("Plugin", Plugin)]


def test_keys_are_the_plugin_names() -> None:
    assert list(_registry_with_plugin().keys()) == ["Plugin"]


def test_get_returns_the_registered_object() -> None:
    assert _registry_with_plugin().get("Plugin") is Plugin


def test_get_returns_the_default_for_an_unknown_name() -> None:
    registry = _registry_with_plugin()

    assert registry.get("bla") is None
    assert registry.get("bla", "blub") == "blub"


class InstanceRegistry(cmk.ccc.plugin_registry.Registry[Plugin]):
    @override
    def plugin_name(self, instance: Plugin) -> str:
        return instance.__class__.__name__
