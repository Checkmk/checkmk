#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final, Generic, Protocol, TypeVar

from ._wellknown import CMK_ADDONS_PLUGINS, CMK_PLUGINS, PluginGroup


class _PluginProtocol(Protocol):
    @property
    def name(self) -> Hashable: ...


_PluginType = TypeVar("_PluginType", bound=_PluginProtocol)


class _ImporterProtocol(Protocol):
    def __call__(self, module_name: str, raise_errors: bool) -> ModuleType | None: ...


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
    plugin_group: PluginGroup,
    plugin_prefixes: Mapping[type[_PluginType], str],
    raise_errors: bool,
) -> DiscoveredPlugins[_PluginType]:
    """Collect all plugins from well-known locations"""

    module_names_by_priority = discover_modules(plugin_group, raise_errors=raise_errors)

    collector = Collector(plugin_prefixes, raise_errors=raise_errors)
    for mod_name in module_names_by_priority:
        collector.add_from_module(mod_name, _import_optionally)

    return DiscoveredPlugins(collector.errors, collector.plugins)


def _ls_defensive(path: str) -> Sequence[str]:
    try:
        return list(os.listdir(path))
    except (FileNotFoundError, NotADirectoryError):
        return []


def discover_families(
    *,
    raise_errors: bool,
    modules: Iterable[ModuleType] | None = None,
    ls: Callable[[str], Iterable[str]] = _ls_defensive,
) -> Mapping[str, Sequence[str]]:
    """Discover all families below `modules` and their paths"""
    if modules is None:
        modules = [
            m
            for m in (
                _import_optionally(CMK_PLUGINS, raise_errors=raise_errors),
                _import_optionally(CMK_ADDONS_PLUGINS, raise_errors=raise_errors),
            )
            if m is not None
        ]

    family_paths = defaultdict(list)
    for module in modules:
        for path in module.__path__:
            for family in ls(path):
                family_paths[f"{module.__name__}.{family}"].append(f"{path}/{family}")

    return family_paths


def discover_modules(
    plugin_group: PluginGroup,
    *,
    raise_errors: bool,
    modules: Iterable[ModuleType] | None = None,
    ls: Callable[[str], Iterable[str]] = _ls_defensive,
) -> Iterable[str]:
    """Discover all potetial plug-in modules blow `modules`.

    Returned iterable should be deduplicated.
    """
    return _deduplicate(
        (
            f"{family}.{plugin_group.value}.{fname.removesuffix('.py')}"
            for family, paths in discover_families(
                raise_errors=raise_errors, modules=modules, ls=ls
            ).items()
            for path in paths
            for fname in ls(f"{path}/{plugin_group.value}")
            if fname not in {"__pycache__", "__init__.py"}
        )
    )


def plugins_local_path() -> Path | None:
    """Return the first local path for cmk plugins

    Currently there is always exactly one.
    """
    return (
        None
        if (raw_local := _first_writable_safe_python_path()) is None
        else Path(raw_local, *CMK_PLUGINS.split("."))
    )


def addons_plugins_local_path() -> Path | None:
    """Return the first local path for cmk addon plugins

    Currently there is always exactly one.
    """
    return (
        None
        if (raw_local := _first_writable_safe_python_path()) is None
        else Path(raw_local, *CMK_ADDONS_PLUGINS.split("."))
    )


def _first_writable_safe_python_path() -> str | None:
    """Return the best guess for the `local` path

    It's the first writable path in sys.path, omitting '.'.
    """
    return next((p for p in sys.path if p and os.access(p, os.W_OK)), None)


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
    except ModuleNotFoundError as exc:
        if module_name.startswith(str(exc.name)):
            return None  # never choke upon empty/non-existing folders.
        raise  # re-raise exeptions of wrong imports in the module we're importing
    except Exception:
        if raise_errors:
            raise
        return None


class Collector(Generic[_PluginType]):
    def __init__(
        self,
        plugin_prefixes: Mapping[type[_PluginType], str],
        raise_errors: bool,
    ) -> None:
        # Transform plug-in types / prefixes to the data structure we
        # need for this algorithm.
        # We pass them differently to help the type inference along.
        # Other approaches require even worse explicit type annotations
        # on caller side.
        self._prefix_to_types = tuple(
            (prefix, tuple(t for t, p in plugin_prefixes.items() if p == prefix))
            for prefix in set(plugin_prefixes.values())
        )
        self.raise_errors: Final = raise_errors

        self.errors: list[Exception] = []
        self._unique_plugins: dict[
            tuple[type[_PluginType], Hashable], tuple[PluginLocation, _PluginType]
        ] = {}

    @property
    def plugins(self) -> Mapping[PluginLocation, _PluginType]:
        return dict(self._unique_plugins.values())

    def add_from_module(self, mod_name: str, importer: _ImporterProtocol) -> None:
        try:
            module = importer(mod_name, raise_errors=True)
        except Exception as exc:
            exc_sub = type(exc)(f"{mod_name}: {exc}")
            self._handle_error(exc_sub)
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
            try:
                plugin_types = next(
                    types for prefix, types in self._prefix_to_types if name.startswith(prefix)
                )
            except StopIteration:
                continue  # no match

            location = PluginLocation(module_name, name)
            if not isinstance(value, plugin_types):
                self._handle_error(TypeError(f"{location}: {value!r}"))
                continue

            key = (value.__class__, value.name)
            if (existing := self._unique_plugins.get(key)) is not None:
                self._handle_error(
                    ValueError(
                        f"{location}: plug-in '{value.name}' already defined at {existing[0]}"
                    )
                )

            self._unique_plugins[key] = (location, value)

    def _handle_error(self, exc: Exception) -> None:
        if self.raise_errors:
            raise exc
        self.errors.append(exc)
