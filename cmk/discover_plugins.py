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
from types import ModuleType
from typing import Generic, TypeVar

PLUGIN_BASE = "cmk.plugins"


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
    """Load all specified packages"""

    try:
        plugin_base = importlib.import_module(PLUGIN_BASE)
    except Exception as exc:
        if raise_errors:
            raise
        return DiscoveredPlugins((exc,), {})

    errors = []
    plugins: dict[PluginLocation, _PluginType] = {}
    for pkg_name in _find_namespaces(plugin_base, plugin_group):
        try:
            module = importlib.import_module(pkg_name)
        except ModuleNotFoundError:
            pass  # don't choke upon empty folders.
        except Exception as exc:
            if raise_errors:
                raise
            errors.append(exc)
            continue

        module_errors, module_plugins = _collect_module_plugins(
            pkg_name, vars(module), name_prefix, plugin_type, raise_errors
        )
        errors.extend(module_errors)
        plugins.update(module_plugins)

    return DiscoveredPlugins(errors, plugins)


def _find_namespaces(plugin_base: ModuleType, plugin_group: str) -> set[str]:
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


def _collect_module_plugins(
    module_name: str,
    objects: Mapping[str, object],
    name_prefix: str,
    plugin_type: type[_PluginType],
    raise_errors: bool,
) -> tuple[Sequence[Exception], Mapping[PluginLocation, _PluginType]]:
    """Dispatch valid and invalid well-known objects

    >>> errors, plugins = _collect_module_plugins("my_module", {"my_plugin": 1, "my_b": "two", "some_c": "ignored"}, "my_", int, False)
    >>> errors[0]
    TypeError("my_module:my_b: 'two'")
    >>> plugins
    {PluginLocation(module='my_module', name='my_plugin'): 1}
    """
    errors = []
    plugins = {}

    for name, value in objects.items():
        if not name.startswith(name_prefix):
            continue

        location = PluginLocation(module_name, name)
        if isinstance(value, plugin_type):
            plugins[location] = value
            continue

        if raise_errors:
            raise TypeError(f"{location}: {value!r}")

        errors.append(TypeError(f"{location}: {value!r}"))

    return errors, plugins
