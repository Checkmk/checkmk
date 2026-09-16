#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"


from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Final, override

from cmk.bakery.v1 import (
    PkgStep,
    WindowsConfigContent,
)

from ._constants import (
    ScriptType,
)

YamlScriptValueType = int | str | bool


class ScriptletHandle:
    def __init__(
        self,
        step: PkgStep,
        lines: Iterable[str],
        depends_on: Iterable[str] | None = None,
    ) -> None:
        self.lines: Final = lines
        self.step: Final = step
        self.depends_on: Final = set(depends_on) if depends_on else None

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(step={self.step!r}, lines={self.lines!r}, depends_on={self.depends_on!r})"

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class ABCYamlConfig(ABC):
    def __init__(self, path: Sequence[str]) -> None:
        if len(path) < 2:
            raise ValueError(
                "Minumum path length for Windows configuration entry is 2 (i.e. section/name)"
            )
        if len(path) > 3:
            raise ValueError(
                "Maximum path length for Windows configuration is 3 (i.e. section/subsection/name)"
            )
        self._path = path

    @abstractmethod
    def process(self, yml_store: YamlStore) -> None:
        pass


class YamlEntry(ABCYamlConfig):
    def __init__(self, path: list[str], content: WindowsConfigContent) -> None:
        super().__init__(path)
        self._content = content

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path!r}, content={self._content!r})"

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
    def process(self, yml_store: YamlStore) -> None:
        yml_store.set_content(self._path, self._content)


class YamlItems(ABCYamlConfig):
    def __init__(self, path: Sequence[str], content: Sequence[WindowsConfigContent]) -> None:
        super().__init__(path)
        self._content = list(content)

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path!r}, content={self._content!r})"

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
    def process(self, yml_store: YamlStore) -> None:
        yml_store.insert_content(self._path, self._content)


class YamlPluginSettings:
    def __init__(
        self, plugin_type: ScriptType, pattern: str, *, name: str, value: YamlScriptValueType
    ) -> None:
        self._plugin_type = plugin_type
        self._pattern = pattern
        self._name = name
        self._value = value

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"plugin_type={self._plugin_type!r}, "
            f"pattern={self._pattern!r}, "
            f"name={self._name!r}, "
            f"value={self._value!r})"
        )

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def process(self, yml_store: YamlStore) -> None:
        yml_store.add_plugins_entry(
            self._plugin_type,
            self._pattern,
            name=self._name,
            value=self._value,
        )


class YamlStore:
    _TYPE_TO_SECTION: Final = {ScriptType.PLUGIN: "plugins", ScriptType.LOCAL: "local"}
    _TYPE_TO_PREFIX: Final = {ScriptType.PLUGIN: "$CUSTOM_PLUGINS_PATH$\\", ScriptType.LOCAL: ""}

    def __init__(self) -> None:
        self._yml_store: dict[str, dict] = {}

    def get_yml(self) -> dict:
        return self._yml_store

    def make_target(self, path: Sequence[str]) -> dict:
        target = self.get_yml()
        for entry in path:
            if entry not in target:
                target[entry] = {}
            target = target[entry]
        return target

    def set_content(
        self,
        path: Sequence[str],
        content: WindowsConfigContent,
    ) -> None:
        target = self.make_target(path[:-1])
        target[path[-1]] = content

    def insert_content(self, path: Sequence[str], content: WindowsConfigContent) -> None:
        target = self.make_target(path[:-1])
        leaf = path[-1]
        if leaf not in target:
            target[leaf] = []
        target[leaf] += content

    def make_section(self, key_name: str) -> dict:
        if key_name not in self._yml_store:
            self._yml_store[key_name] = {}

        return self._yml_store[key_name]

    def get_value(
        self, section_name: str, sub_section_name: str, key_third: str | None = None
    ) -> WindowsConfigContent | None:
        if section_name not in self._yml_store:
            return None

        section = self._yml_store[section_name]

        if sub_section_name not in section:
            return None

        sub_value = section[sub_section_name]
        if key_third is None:
            return sub_value

        return sub_value.get(key_third, None)

    def make_sub_section(self, section_name: str, sub_section_name: str) -> dict:
        section = self.make_section(section_name)

        if sub_section_name not in section:
            section[sub_section_name] = {}

        return section[sub_section_name]

    def make_sub_list(self, section_name: str, sub_list_name: str) -> list:
        section = self.make_section(section_name)

        if sub_list_name not in section:
            section[sub_list_name] = []

        return section[sub_list_name]

    @staticmethod
    def _add_prefix(plugin_type: ScriptType, pattern: str) -> str:
        if pattern.startswith("\\"):
            return pattern  # names like "\windows\cmd.exe" cannot be prefixed
        if len(pattern) > 1 and pattern[1] == ":":
            return pattern  # names like "C:\windows\cmd.exe" cannot be prefixed too
        return YamlStore._TYPE_TO_PREFIX[plugin_type] + pattern

    def add_plugins_entry(
        self,
        plugin_type: ScriptType,
        pattern: str,
        *,
        name: str,
        value: YamlScriptValueType,
    ) -> None:
        section_name: Final = YamlStore._TYPE_TO_SECTION[plugin_type]
        section = self.make_section(section_name)
        section["enabled"] = True
        entries = self.make_sub_list(section_name, "execution")
        active_pattern = YamlStore._add_prefix(plugin_type, pattern)

        for e in entries:
            if e["pattern"] == active_pattern:
                e[name] = value
                return
        entries.append({"pattern": active_pattern, "run": True, name: value})
