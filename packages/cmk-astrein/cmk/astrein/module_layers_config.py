#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Domain types and loader for module layer architecture rules.

The architectural rules (components, allowed imports, etc.) are defined
declaratively in module_layers.toml at the repository root and loaded
by ``load_config``.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, override, Protocol

CONFIG_FILENAME = "module_layers.toml"


class ModulePath(Path):
    def is_below(self, path: str) -> bool:
        return is_prefix_of(Path(path).parts, self.parts)


class Component:
    def __init__(self, name: str):
        self.name: Final = name
        self.parts: Final = tuple(name.split("."))

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    @override
    def __str__(self) -> str:
        return self.name

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Component):
            return NotImplemented
        return self.parts == other.parts

    @override
    def __hash__(self) -> int:
        return hash(self.parts)

    def is_below(self, component: str | Component) -> bool:
        component = component if isinstance(component, Component) else Component(component)
        return is_prefix_of(component.parts, self.parts)


class ModuleName:
    def __init__(self, name: str):
        self.name: Final = name
        self.parts: Final = tuple(name.split("."))

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    @override
    def __str__(self) -> str:
        return self.name

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleName):
            return NotImplemented
        return self.parts == other.parts

    def in_component(self, component: Component) -> bool:
        return is_prefix_of(component.parts, self.parts)


class ImportCheckerProtocol(Protocol):
    def __call__(
        self,
        *,
        imported: ModuleName,
        component: Component | None,
    ) -> bool: ...


def is_prefix_of[T](x: Sequence[T], y: Sequence[T]) -> bool:
    return x == y[: len(x)]


def get_absolute_importee(
    *,
    root_name: str,
    modname: str,
    level: int,
    is_package: bool,
) -> ModuleName:
    parent = root_name.rsplit(".", level - is_package)[0]
    return ModuleName(f"{parent}.{modname}")


def _allow(
    *modules: str,
    exclude: tuple[str, ...] = (),
) -> ImportCheckerProtocol:
    # I don't like having to support excludes, but the current rule for
    # `gui` is everything from "self" but not "cmk.gui.plugins"
    allowed = {Component(m) for m in modules}
    forbidden = {Component(m) for m in exclude}

    def _is_allowed(
        *,
        imported: ModuleName,
        component: Component | None,
    ) -> bool:
        if any(imported.in_component(m) for m in forbidden):
            return False
        return (component is not None and imported.in_component(component)) or any(
            imported.in_component(m) for m in allowed
        )

    return _is_allowed


@dataclass(frozen=True)
class ModuleLayersConfig:
    """Parsed module layer architecture configuration."""

    first_party: tuple[Component, ...]
    components: Mapping[Component, ImportCheckerProtocol]
    file_components: Mapping[ModulePath, Component]
    file_dependencies: Mapping[ModulePath, ImportCheckerProtocol]


def _expand_allows(
    allows: list[str],
    groups: Mapping[str, list[str]],
) -> list[str]:
    """Expand @group references in an allows list."""
    result: list[str] = []
    for item in allows:
        if item.startswith("@"):
            group_name = item[1:]
            try:
                result.extend(groups[group_name])
            except KeyError:
                raise ValueError(f"Unknown group reference: {item!r}") from None
        else:
            result.append(item)
    return result


def _build_checker(
    entry: Mapping[str, object],
    groups: Mapping[str, list[str]],
) -> ImportCheckerProtocol:
    if entry.get("allow_all"):
        return lambda *, imported, component: True  # noqa: ARG005

    raw_allows = entry.get("allows")
    if raw_allows is None:
        raise ValueError("Component entry must have 'allows' or 'allow_all'")
    if not isinstance(raw_allows, list):
        raise TypeError(f"'allows' must be a list, got {type(raw_allows).__name__}")

    expanded = _expand_allows(raw_allows, groups)
    excludes = entry.get("excludes", [])
    if not isinstance(excludes, list):
        raise TypeError(f"'excludes' must be a list, got {type(excludes).__name__}")

    return _allow(*expanded, exclude=tuple(excludes))


def _build_plugin_components(
    plugin_families: Mapping[str, object],
    groups: Mapping[str, list[str]],
) -> dict[Component, ImportCheckerProtocol]:
    result: dict[Component, ImportCheckerProtocol] = {}

    plugin_api_modules = _expand_allows(["@plugin_apis"], groups)
    base_allows = [*plugin_api_modules, "cmk.plugins.lib"]

    clean = plugin_families.get("clean", [])
    if not isinstance(clean, list):
        raise TypeError(f"plugin_families.clean must be a list, got {type(clean).__name__}")

    for family in clean:
        result[Component(f"cmk.plugins.{family}")] = _allow(*base_allows)

    violations = plugin_families.get("violations", {})
    if not isinstance(violations, dict):
        raise TypeError(
            f"plugin_families.violations must be a table, got {type(violations).__name__}"
        )

    for family, entry in violations.items():
        if not isinstance(entry, dict):
            raise TypeError(
                f"plugin_families.violations.{family} must be a table, got {type(entry).__name__}"
            )
        extra_allows = entry.get("allows", [])
        if not isinstance(extra_allows, list):
            raise TypeError(
                f"plugin_families.violations.{family}.allows must be a list, "
                f"got {type(extra_allows).__name__}"
            )
        expanded_extra = _expand_allows(extra_allows, groups)
        result[Component(f"cmk.plugins.{family}")] = _allow(*base_allows, *expanded_extra)

    return result


type _TomlDict = dict[str, object]


def _parse_components(
    data: _TomlDict, groups: Mapping[str, list[str]]
) -> dict[Component, ImportCheckerProtocol]:
    """Parse [components] and [plugin_families] into a specificity-sorted mapping.

    More specific components (more dotted parts) come first so that
    ``_find_component`` returns the most specific match.
    """
    components: dict[Component, ImportCheckerProtocol] = {}

    raw_components: _TomlDict = data.get("components", {})  # type: ignore[assignment]
    for comp_name, entry in raw_components.items():
        if not isinstance(entry, dict):
            raise TypeError(f"components.{comp_name!r} must be a table, got {type(entry).__name__}")
        components[Component(comp_name)] = _build_checker(entry, groups)

    plugin_families: _TomlDict = data.get("plugin_families", {})  # type: ignore[assignment]
    if plugin_families:
        components.update(_build_plugin_components(plugin_families, groups))

    return dict(sorted(components.items(), key=lambda kv: len(kv[0].parts), reverse=True))


def _parse_file_components(data: _TomlDict) -> dict[ModulePath, Component]:
    result: dict[ModulePath, Component] = {}
    raw: _TomlDict = data.get("file_components", {})  # type: ignore[assignment]
    for path_str, comp_name in raw.items():
        if not isinstance(comp_name, str):
            raise TypeError(
                f"file_components.{path_str!r} must be a string, got {type(comp_name).__name__}"
            )
        result[ModulePath(path_str)] = Component(comp_name)
    return result


def _parse_file_dependencies(
    data: _TomlDict, groups: Mapping[str, list[str]]
) -> dict[ModulePath, ImportCheckerProtocol]:
    result: dict[ModulePath, ImportCheckerProtocol] = {}
    raw: _TomlDict = data.get("file_dependencies", {})  # type: ignore[assignment]
    for path_str, entry in raw.items():
        if not isinstance(entry, dict):
            raise TypeError(
                f"file_dependencies.{path_str!r} must be a table, got {type(entry).__name__}"
            )
        result[ModulePath(path_str)] = _build_checker(entry, groups)
    return result


def _parse_first_party(data: _TomlDict) -> tuple[Component, ...]:
    raw = data.get("first_party", ["cmk"])
    if not isinstance(raw, list) or not all(isinstance(name, str) for name in raw):
        raise TypeError("'first_party' must be a list of strings")
    return tuple(Component(name) for name in raw)


def load_config(config_path: Path) -> ModuleLayersConfig:
    """Load and parse module_layers.toml into runtime configuration."""
    with config_path.open("rb") as f:
        data = tomllib.load(f)

    groups: dict[str, list[str]] = data.get("groups", {})

    return ModuleLayersConfig(
        first_party=_parse_first_party(data),
        components=_parse_components(data, groups),
        file_components=_parse_file_components(data),
        file_dependencies=_parse_file_dependencies(data, groups),
    )
