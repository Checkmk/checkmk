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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Final, Generic, Protocol, TypeVar

PLUGIN_NAMESPACES = ("cmk.plugins", "cmk_addons.plugins")


class _PluginProtocol(Protocol):
    @property
    def name(self) -> str:
        ...


_PluginType = TypeVar("_PluginType", bound=_PluginProtocol)


class ImporterProtocol(Protocol):
    def __call__(self, module_name: str, raise_errors: bool) -> ModuleType | None:
        ...


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

    modules = (
        m
        for p_namespace in PLUGIN_NAMESPACES
        if (m := _import_optionally(p_namespace, raise_errors)) is not None
    )
    namespaces_by_priority = find_namespaces(modules, plugin_group, ls=_ls_defensive)

    collector = Collector(plugin_type, name_prefix, raise_errors=raise_errors)
    for mod_name in namespaces_by_priority:
        collector.add_from_module(mod_name, _import_optionally)

    return DiscoveredPlugins(collector.errors, collector.plugins)


def find_namespaces(
    modules: Iterable[ModuleType],
    plugin_group: str,
    *,
    ls: Callable[[str], Iterable[str]],
) -> Iterable[str]:
    """Find all potetial namespaces implied by the passed modules.

    Returned iterable should be deduplicated.
    """
    return _deduplicate(
        (
            f"{module.__name__}.{family}.{plugin_group}.{fname.removesuffix('.py')}"
            for module in modules
            for path in module.__path__
            for family in ls(path)
            for fname in ls(f"{path}/{family}/{plugin_group}")
            if fname not in {"__pycache__", "__init__.py"}
        )
    )


_T = TypeVar("_T")


def _deduplicate(iterable: Iterable[_T]) -> Iterable[_T]:
    """Deduplicate preserving order

    >>> list(_deduplicate([2, 1, 2, 3, 3, 1]))
    [2, 1, 3]
    """
    return dict.fromkeys(iterable)


def _import_optionally(module_name: str, raise_errors: bool) -> ModuleType | None:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None  # never choke upon empty/non-existing folders.
    except Exception as _exc:
        if raise_errors:
            raise
        return None


def _ls_defensive(path: str) -> Sequence[str]:
    try:
        return list(os.listdir(path))
    except FileNotFoundError:
        return []


class Collector(Generic[_PluginType]):
    def __init__(
        self,
        plugin_type: type[_PluginType],
        name_prefix: str,
        *,
        raise_errors: bool,
    ) -> None:
        self.plugin_type: Final = plugin_type
        self.name_prefix: Final = name_prefix
        self.raise_errors: Final = raise_errors

        self.errors: list[Exception] = []
        self._unique_plugins: dict[
            tuple[type[_PluginType], str], tuple[PluginLocation, _PluginType]
        ] = {}

    @property
    def plugins(self) -> Mapping[PluginLocation, _PluginType]:
        return dict(self._unique_plugins.values())

    def add_from_module(self, mod_name: str, importer: ImporterProtocol) -> None:
        try:
            module = importer(mod_name, raise_errors=True)
        except Exception as exc:
            self._handle_error(exc)
            return

        if module is None:
            return

        self._collect_module_plugins(mod_name, vars(module))

    def _collect_module_plugins(
        self,
        module_name: str,
        objects: Mapping[str, object],
    ) -> None:
        """Dispatch valid and invalid well-known objects"""
        for name, value in objects.items():
            if not name.startswith(self.name_prefix):
                continue

            location = PluginLocation(module_name, name)
            if not isinstance(value, self.plugin_type):
                self._handle_error(TypeError(f"{location}: {value!r}"))
                continue

            key = (value.__class__, value.name)
            if (existing := self._unique_plugins.get(key)) is not None:
                self._handle_error(
                    ValueError(
                        f"{location}: plugin '{value.name}' already defined at {existing[0]}"
                    )
                )

            self._unique_plugins[key] = (location, value)

    def _handle_error(self, exc: Exception) -> None:
        if self.raise_errors:
            raise exc
        self.errors.append(exc)
