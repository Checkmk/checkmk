import pytest

import cmk.utils.plugin_registry


class Plugin(object):
    pass


class PluginRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return Plugin

    def _register(self, plugin_class):
        self._entries[plugin_class.__name__] = plugin_class


@pytest.fixture(scope="module")
def basic_registry():
    registry = PluginRegistry()
    registry.register_plugin(Plugin)
    return registry


def test_initialization():
    registry = PluginRegistry()
    assert registry.items() == []


def test_decorator_registration():
    registry = PluginRegistry()
    assert registry.items() == []

    @registry.register
    class DecoratedPlugin(Plugin):
        pass

    assert registry.get("DecoratedPlugin") == DecoratedPlugin


def test_method_registration():
    registry = PluginRegistry()
    assert registry.items() == []

    class MethodRegisteredPlugin(Plugin):
        pass

    registry.register_plugin(MethodRegisteredPlugin)
    assert registry.get("MethodRegisteredPlugin") == MethodRegisteredPlugin


def test_contains(basic_registry):
    assert "bla" not in basic_registry
    assert "Plugin" in basic_registry


def test_delitem(basic_registry):
    with pytest.raises(KeyError):
        del basic_registry["bla"]

    @basic_registry.register
    class DelPlugin(Plugin):
        pass

    del basic_registry["DelPlugin"]


def test_getitem(basic_registry):
    with pytest.raises(KeyError):
        _unused = basic_registry["bla"]

    assert basic_registry["Plugin"] == Plugin


def test_values(basic_registry):
    assert basic_registry.values() == [Plugin]


def test_items(basic_registry):
    assert basic_registry.items() == [("Plugin", Plugin)]


def test_keys(basic_registry):
    assert basic_registry.keys() == ["Plugin"]


def test_get(basic_registry):
    assert basic_registry.get("bla") is None
    assert basic_registry.get("bla", "blub") == "blub"

    assert basic_registry.get("Plugin") == Plugin
