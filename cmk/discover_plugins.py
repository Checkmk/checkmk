#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Loading API based plugins from cmk.plugins

This implements common logic for loading API based plugins
(yes, we have others) from cmk.plugins.

We have more "plugin" loading logic else where, but there
are subtle differences with respect to the treatment of
namespace packages and error handling.

Changes in this file might result in different behaviour
of plugins developed against a versionized API.

Please keep this in mind when trying to consolidate.
"""
import importlib
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Generic, LiteralString, TypeVar

SHIPPED_PLUGINS = "cmk.plugins"


_PluginType = TypeVar("_PluginType")


@dataclass(frozen=True)
class PluginLocation:
    module: str
    name: str | None = None

    def __str__(self) -> str:
        return f"{self.module}:{self.name}"


@dataclass(frozen=True)
class DiscoveredPlugins(Generic[_PluginType]):
    errors: Sequence[Exception]
    plugins: Mapping[PluginLocation, _PluginType]


def discover_plugins(
    plugin_group: str,
    name_prefix: str,
    plugin_type: type[_PluginType],
    *,
    raise_errors: bool,
) -> DiscoveredPlugins[_PluginType]:
    """Collect all plugins from well-known locations"""

    collector = _Collector(plugin_type, name_prefix, raise_errors)

    for mod_name in _find_namespaces(SHIPPED_PLUGINS, plugin_group, raise_errors):
        collector.add_from_module(mod_name)

    return DiscoveredPlugins(collector.errors, collector.plugins)


def _find_namespaces(
    base_namespace: LiteralString, plugin_group: str, raise_errors: bool
) -> set[str]:
    try:
        plugin_base = importlib.import_module(base_namespace)
    except Exception as _exc:
        if raise_errors:
            raise
        return set()

    return {
        f"{plugin_base.__name__}.{family}.{plugin_group}.{fname.removesuffix('.py')}"
        for path in plugin_base.__path__
        for family in _ls_defensive(path)
        for fname in _ls_defensive(f"{path}/{family}/{plugin_group}")
        if fname not in {"__pycache__", "__init__.py"}
    }


def _ls_defensive(path: str) -> Sequence[str]:
    try:
        return list(os.listdir(path))
    except FileNotFoundError:
        return []


class _Collector(Generic[_PluginType]):
    def __init__(
        self,
        plugin_type: type[_PluginType],
        name_prefix: str,
        raise_errors: bool,
    ) -> None:
        self.plugin_type: Final = plugin_type
        self.name_prefix: Final = name_prefix
        self.raise_errors: Final = raise_errors

        self.errors: list[Exception] = []
        self.plugins: dict[PluginLocation, _PluginType] = {}

    def add_from_module(self, mod_name: str) -> None:
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            pass  # don't choke upon empty folders.
        except Exception as exc:
            if self.raise_errors:
                raise
            self.errors.append(exc)
            return

        self._collect_module_plugins(mod_name, vars(module))

    def _collect_module_plugins(
        self,
        module_name: str,
        objects: Mapping[str, object],
    ) -> None:
        """Dispatch valid and invalid well-known objects

        >>> collector = _Collector(plugin_type=int, name_prefix="my_", raise_errors=False)
        >>> collector._collect_module_plugins(
        ...     "my_module",
        ...     {
        ...         "my_plugin": 1,
        ...         "my_b": "two",
        ...         "some_c": "ignored",
        ...     },
        ... )
        >>> collector.errors[0]
        TypeError("my_module:my_b: 'two'")
        >>> collector.plugins
        {PluginLocation(module='my_module', name='my_plugin'): 1}
        """
        for name, value in objects.items():
            if not name.startswith(self.name_prefix):
                continue

            location = PluginLocation(module_name, name)
            if isinstance(value, self.plugin_type):
                self.plugins[location] = value
                continue

            if self.raise_errors:
                raise TypeError(f"{location}: {value!r}")

            self.errors.append(TypeError(f"{location}: {value!r}"))
