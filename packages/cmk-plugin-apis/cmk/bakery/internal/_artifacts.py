#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Final, override, TypedDict

from cmk.bakery.v1 import (
    OS,
    PkgStep,
    WindowsConfigContent,
)

from ._constants import (
    AGENT_FILE_HEADER,
    LogicalPath,
    ScriptType,
)
from ._types import AgentConfig

YamlScriptValueType = int | str | bool


@dataclass(frozen=True)
class AgentFileLocator:
    agents_dir: Path
    local_agents_dir: Path
    agents_wellknown_path_segment: str

    def get_source_path(self, container: ABCFileContainer) -> Path | None:
        return (
            self._get_v1_source_path(container)
            if container.plugin_module is None
            else self._get_v2_source_path(container.plugin_module, container.content.source)
        )

    def _get_v1_source_path(self, container: ABCFileContainer) -> Path | None:
        if (rel_source := container.relative_source_path()) is None:
            return None

        for source_location in self._v1_folders(container.base_os):
            source_file = source_location / rel_source.parent / "signed" / rel_source.name
            if source_file.exists():
                return source_file
            source_file = source_location / rel_source
            if source_file.exists():
                return source_file

        raise FileNotFoundError("Agent file not found: %s" % rel_source)

    def _v1_folders(self, os: OS) -> Iterable[Path]:
        if os is OS.WINDOWS:
            yield from self.windows_agent_folders()
        yield self.local_agents_dir
        yield self.agents_dir

    def windows_agent_folders(self) -> Iterable[Path]:
        return (
            self.local_agents_dir / "windows",
            self.agents_dir / "windows",
        )

    def _get_v2_source_path(self, plugin_module: str, source: Path | None) -> Path | None:
        if source is None:
            return None
        # All signed plugins are deployed to a single well-known location by
        # the build/install pipeline (signed_plugins.tar), regardless of where
        # the v2 module originally lives. This path may change in the future.
        signed = self.agents_dir / "windows/plugins/signed" / source.name
        if signed.exists():
            return signed
        return self._get_v2_folder(plugin_module) / source

    def _get_v2_folder(self, module_name: str) -> Path:
        file = self._module_file(module_name)
        bakery_plugins_dir = file.parent.parent if file.name == "__init__.py" else file.parent
        return bakery_plugins_dir.parent / self.agents_wellknown_path_segment

    @staticmethod
    def _module_file(module_name: str) -> Path:
        if (file := import_module(module_name).__file__) is None:
            # should never happen: we know we loaded this from a file.
            raise TypeError(f"module does not have a __file__ attrbute: {module_name}")
        return Path(file)


class ABCBakeryFile(ABC):
    """Represents a file that is managed by the bakery and will be added to the agents.
    This class and it's subclasses contain methods for operations on the files itself.
    It is meant to be used as content for ABCFileContainer instances.
    """

    def __init__(self, base_os: OS, target: Path) -> None:
        super().__init__()
        self.base_os: Final[OS] = base_os
        self.target: Final[Path] = target
        self.source: Path | None = None

    # overwrite in subclass if applicable
    def add_to_line_mapping(self, _: Mapping[str, str]) -> None:
        pass

    def place(
        self,
        source_path: Path | None,
        target_location: Path,
        permissions: int,
        preserve_executable: bool,
    ) -> None:
        target_path = self._get_target_path(target_location)
        self._specific_place(source_path, target_path)
        if self.base_os is not OS.WINDOWS:
            self._set_file_permissions(target_path, permissions, preserve_executable)

    @abstractmethod
    def _specific_place(self, source_path: Path | None, target_path: Path) -> None:
        pass

    def _get_target_path(self, target_location: Path) -> Path:
        target_path = target_location / self.target
        target_path.parent.mkdir(exist_ok=True, parents=True)
        return target_path

    @staticmethod
    def _set_file_permissions(
        target_path: Path,
        permissions: int,
        preserve_executable: bool,
    ) -> None:
        if preserve_executable:
            executable_flags = target_path.stat().st_mode & 0o111
            target_path.chmod(permissions | executable_flags)
            return

        target_path.chmod(permissions)


class ABCFileContainer(ABC):
    """Represents the attributes of agent files managed by the bakery,
    including the file itself.
    Depending on the file category, different attributes need to be managed.
    This class (and it's subclasses) contains methods for the proper evaluation
    of all attributes and configs that incluence the adaption and placement of the
    underlying ABCBakeryFile.
    """

    _not_set = object()

    def __init__(
        self,
        content: ABCBakeryFile,
        plugin_module: str | None,
        logical_path: LogicalPath,
        preserve_executable: bool = False,
    ) -> None:
        self.content: Final = content
        self.plugin_module: Final = plugin_module
        self.logical_path: Final = logical_path
        self._preserve_executable: Final = preserve_executable

    @property
    def base_os(self) -> OS:
        return self.content.base_os

    def source_path(self, locator: AgentFileLocator) -> Path | None:
        # Can't be inlined, or we break a RMK hack where we override this.
        return locator.get_source_path(self)

    def place(
        self,
        pkg_root: Path,
        locator: AgentFileLocator,
        target_location: Path,
        unix_permissions: int,
    ) -> None:
        self.content.place(
            self.source_path(locator),
            pkg_root / self._specific_target_location(target_location),
            unix_permissions,
            self._preserve_executable,
        )

    def apply_config(self, yml_store: YamlStore) -> None:
        pass

    def relative_source_path(self) -> Path | None:
        return self.content.source

    def _specific_target_location(self, target_location: Path) -> Path:
        return target_location


class IntervalConfig(TypedDict):
    override: bool
    pattern: str
    interval: int


class PluginContainer(ABCFileContainer):
    def __init__(
        self,
        agconf: AgentConfig,
        content: ABCBakeryFile,
        plugin_module: str | None,
        *,
        interval: int | None = None,
        asynchronous: bool | None = None,
        timeout: int | None = None,
        retry_count: int | None = None,
    ) -> None:
        super().__init__(
            content=content, plugin_module=plugin_module, logical_path=LogicalPath.PLUGINS
        )

        self._agconf = agconf
        self._interval = interval
        self._asynchronous: Final[bool | None] = asynchronous
        self._timeout: Final[int | None] = timeout
        self._retry_count: Final[int | None] = retry_count

        self._apply_generic_rules(agconf)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"agconf={self._agconf!r}, "
            f"content={self.content!r}, "
            f"interval={self._interval!r}, "
            f"asynchronous={self._asynchronous!r}, "
            f"timeout={self._timeout!r}, "
            f"retry_count={self._retry_count!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def _apply_generic_rules(self, agconf: AgentConfig) -> None:
        self._apply_unix_custom_intervals(agconf)

    def _apply_unix_custom_intervals(self, agconf: AgentConfig) -> None:
        if self.base_os is OS.WINDOWS:
            return
        for entry in agconf.get("unix_plugins_cache_age", []):
            self._apply_unix_custom_interval(entry)

    def _apply_unix_custom_interval(self, interval_config: IntervalConfig) -> None:
        if self._interval and not interval_config["override"]:
            return

        if self.content.target.match(interval_config["pattern"]):
            self._interval = interval_config["interval"]

    def apply_config(self, yml_store: YamlStore) -> None:
        if any((self._asynchronous, self._interval, self._timeout, self._retry_count)):
            execution = yml_store.make_sub_list("plugins", "execution")
            entry = self._create_plugin_execution_entry(
                base_name=str(self.content.target),
                asynchronous=self._asynchronous,
                cache_age=self._interval,
                timeout=self._timeout,
                retry_count=self._retry_count,
            )
            execution.append(entry)

    @override
    def relative_source_path(self) -> Path | None:
        return None if self.content.source is None else ("plugins" / self.content.source)

    def _specific_target_location(self, target_location: Path) -> Path:
        if self.base_os is OS.WINDOWS:
            return target_location
        return target_location / Path(str(self._interval or ""))

    @staticmethod
    def _create_plugin_execution_entry(
        base_name: str,
        *,
        asynchronous: bool | None = None,
        cache_age: int | None = None,
        timeout: int | None = None,
        retry_count: int | None = None,
    ) -> dict:
        entry: dict = {"pattern": "$CUSTOM_PLUGINS_PATH$\\" + base_name}

        if asynchronous is not None:
            entry["async"] = asynchronous
        if cache_age is not None:
            entry["cache_age"] = cache_age
        if timeout is not None:
            entry["timeout"] = timeout
        if retry_count is not None:
            entry["retry_count"] = retry_count

        return entry


class SystemBinaryContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None, **_kw: Any) -> None:
        super().__init__(content=content, plugin_module=plugin_module, logical_path=LogicalPath.BIN)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class PluginConfigContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None, **_kw: Any) -> None:
        super().__init__(
            content=content, plugin_module=plugin_module, logical_path=LogicalPath.CONFIG
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class SystemConfigContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None) -> None:
        super().__init__(content=content, plugin_module=plugin_module, logical_path=LogicalPath.ETC)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class LibFileContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None) -> None:
        super().__init__(
            content=content,
            plugin_module=plugin_module,
            logical_path=LogicalPath.LIB,
            preserve_executable=True,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class AgentInternalFileContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None) -> None:
        super().__init__(
            content=content,
            plugin_module=plugin_module,
            logical_path=LogicalPath.AGENT,
            preserve_executable=True,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class RootFileContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None, **_kw: Any) -> None:
        super().__init__(
            content=content, plugin_module=plugin_module, logical_path=LogicalPath.ROOT
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


class HomeFileContainer(ABCFileContainer):
    def __init__(self, content: ABCBakeryFile, plugin_module: str | None, **_kw: Any) -> None:
        super().__init__(
            content=content,
            plugin_module=plugin_module,
            logical_path=LogicalPath.HOME,
            preserve_executable=True,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def get_derived_containers(self, _locator: AgentFileLocator) -> Iterator[ABCFileContainer]:
        yield from ()


_CUSTOM_BASE_PATH: Final[str] = "custom"

_SEARCH_PATHS: Final[Mapping[LogicalPath, str]] = {
    LogicalPath.LIB: "lib",
    LogicalPath.BIN: "bin",
    LogicalPath.VAR: "var",
    LogicalPath.CONFIG: "config",
    LogicalPath.PLUGINS: "lib/plugins",
    LogicalPath.LOCAL: "lib/local",
}


class CustomFileContainer(ABCFileContainer):
    def __init__(
        self,
        content: ABCBakeryFile,
        plugin_module: str | None,
        package: str,
        logical_path: LogicalPath,
    ) -> None:
        super().__init__(
            content=content,
            plugin_module=plugin_module,
            logical_path=logical_path,
            preserve_executable=True,
        )
        self._package = package

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"content={self.content!r}, "
            f"plugin_module={self.plugin_module!r}, "
            f"package={self._package!r}, "
            f"logical_path={self.logical_path!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
    def relative_source_path(self) -> Path | None:
        return (
            None
            if self.content.source is None
            else Path(
                _CUSTOM_BASE_PATH,
                self._package,
                _SEARCH_PATHS[self.logical_path],
                self.content.source,
            )
        )


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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(step={self.step!r}, lines={self.lines!r}, depends_on={self.depends_on!r})"

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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path!r}, content={self._content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def process(self, yml_store: YamlStore) -> None:
        yml_store.set_content(self._path, self._content)


class YamlItems(ABCYamlConfig):
    def __init__(self, path: Sequence[str], content: Sequence[WindowsConfigContent]) -> None:
        super().__init__(path)
        self._content = list(content)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self._path!r}, content={self._content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

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

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"plugin_type={self._plugin_type!r}, "
            f"pattern={self._pattern!r}, "
            f"name={self._name!r}, "
            f"value={self._value!r})"
        )

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

        return sub_value[key_third] if key_third in sub_value else None

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


class FileFromSite(ABCBakeryFile):
    def __init__(
        self,
        base_os: OS,
        source: Path,
        *,
        target: Path | None = None,
        line_mapping: dict[str, str] | None = None,
    ) -> None:
        if target is None:
            target = source
        super().__init__(base_os=base_os, target=target)
        self.source: Path = source
        self._line_mapping = line_mapping or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"source={self.source!r}, "
            f"target={self.target!r}, "
            f"line_mapping={self._line_mapping!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def add_to_line_mapping(self, mapping: Mapping[str, str]) -> None:
        self._line_mapping.update(mapping)

    def _specific_place(self, source_path: Path | None, target_path: Path) -> None:
        assert isinstance(source_path, Path)
        if self._line_mapping:
            self._modify_and_write(source_path, target_path)
            return
        self._simple_copy(source_path, target_path)

    def _simple_copy(self, source_path: Path, target_path: Path) -> None:
        shutil.copy2(source_path, target_path)

    def _modify_and_write(self, source_path: Path, target_path: Path) -> None:
        newline = "\r\n" if self.base_os is OS.WINDOWS else "\n"

        lines = self._get_modified_lines(source_path)

        with target_path.open(mode="w", encoding="utf-8", newline=newline) as targetfile:
            targetfile.write("\n".join(lines) + "\n")

    def _get_modified_lines(self, source_path: Path) -> list[str]:
        def find_mapping(text: str) -> str | None:
            for template, replace_text in self._line_mapping.items():
                if text.startswith(template):
                    return replace_text
            return None

        return [
            find_mapping(line) or line.rstrip()
            for line in source_path.read_text(encoding="utf-8").splitlines()
        ]


class GeneratedTextFile(ABCBakeryFile):
    def __init__(
        self, base_os: OS, lines: Iterable[str], target: Path, include_header: bool = False
    ) -> None:
        super().__init__(base_os=base_os, target=target)
        self._lines = lines
        self._include_header = include_header

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"lines={self._lines!r}, "
            f"target={self.target!r}, "
            f"include_header={self._include_header!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def _specific_place(self, _source_path: object, target_path: Path) -> None:
        newline = "\r\n" if self.base_os is OS.WINDOWS else "\n"

        with target_path.open(mode="w", encoding="utf-8", newline=newline) as tf:
            if self._include_header:
                tf.write(AGENT_FILE_HEADER)
            tf.write("\n".join(self._lines) + "\n")


class GeneratedBinaryFile(ABCBakeryFile):
    def __init__(self, base_os: OS, content: bytes, target: Path) -> None:
        super().__init__(base_os=base_os, target=target)
        self._content = content

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"content={self._content if len(self._content) <= 20 else self._content[:20] + b'...'!r}, "
            f"target={self.target!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def _specific_place(self, _source_path: object, target_path: Path) -> None:
        target_path.write_bytes(self._content)
