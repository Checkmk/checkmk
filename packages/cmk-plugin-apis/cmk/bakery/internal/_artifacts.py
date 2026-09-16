#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"


import shutil
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Final, override

from cmk.bakery.v1 import (
    OS,
    PkgStep,
    WindowsConfigContent,
)

from ._constants import (
    AGENT_FILE_HEADER,
    CUSTOM_FILE_SUBDIRS,
    LogicalPath,
    ScriptType,
)
from ._recipes import PluginExecution

YamlScriptValueType = int | str | bool


@dataclass(frozen=True)
class AgentFileLocator:
    """Find the source file of a container in the Checkmk site.

    The agents folder of the plug-in family the container is bound to is the
    default location. The site's agents directories are the fallback for files
    that belong to no plug-in family, such as the agent itself.
    """

    agents_dir: Path
    local_agents_dir: Path
    agents_wellknown_path_segment: str

    def get_source_path(self, container: FileContainer) -> Path | None:
        if container.content is None or (source := container.content.source) is None:
            return None

        family_file = None
        if container.plugin_module is not None:
            if (
                container.base_os is OS.WINDOWS
                and (signed := self._signed_windows_plugin(source)).exists()
            ):
                return signed
            family_file = self._family_agents_folder(container.plugin_module) / source
            if family_file.exists():
                return family_file

        if (site_file := self._find_in_agents_dirs(container)) is not None:
            return site_file

        raise FileNotFoundError(
            f"Agent file not found: {source} (looked at "
            f"{', '.join(str(f) for f in (family_file, self.local_agents_dir, self.agents_dir) if f)})"
        )

    def _signed_windows_plugin(self, source: Path) -> Path:
        # All signed plugins are deployed to a single well-known location by
        # the build/install pipeline (signed_plugins.tar), regardless of where
        # the plug-in family lives. This path may change in the future.
        return self.agents_dir / "windows/plugins/signed" / source.name

    def _find_in_agents_dirs(self, container: FileContainer) -> Path | None:
        if (rel_source := container.relative_source_path()) is None:
            return None

        for source_location in self._agents_dirs(container.base_os):
            source_file = source_location / rel_source.parent / "signed" / rel_source.name
            if source_file.exists():
                return source_file
            source_file = source_location / rel_source
            if source_file.exists():
                return source_file
        return None

    def _agents_dirs(self, os: OS | None) -> Iterable[Path]:
        if os is OS.WINDOWS:
            yield from self.windows_agent_folders()
        yield self.local_agents_dir
        yield self.agents_dir

    def windows_agent_folders(self) -> Iterable[Path]:
        return (
            self.local_agents_dir / "windows",
            self.agents_dir / "windows",
        )

    def _family_agents_folder(self, module_name: str) -> Path:
        file = self._module_file(module_name)
        bakery_plugins_dir = file.parent.parent if file.name == "__init__.py" else file.parent
        return bakery_plugins_dir.parent / self.agents_wellknown_path_segment

    def _module_file(self, module_name: str) -> Path:
        if (file := import_module(module_name).__file__) is None:
            # should never happen: we know we loaded this from a file.
            raise TypeError(f"module does not have a __file__ attrbute: {module_name}")
        return Path(file)


class ABCBakeryFile(ABC):
    """Represents a file that is managed by the bakery and will be added to the agents.
    This class and it's subclasses contain methods for operations on the files itself.
    It is meant to be used as content for FileContainer instances.
    """

    def __init__(self, base_os: OS, target: Path) -> None:
        super().__init__()
        self.base_os: Final[OS] = base_os
        self.target: Final[Path] = target
        self.source: Path | None = None

    # overwrite in subclass if applicable
    def add_to_line_mapping(self, _: Mapping[str, str]) -> None:
        return

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


class FileContainer:
    """A file the bakery places into an agent package.

    The bakery builds it from a recipe and knows the module of the bakelet the
    recipe came from. A container without content only contributes the stat of
    ``hash_dependency`` to the agent hash.
    """

    def __init__(
        self,
        *,
        content: ABCBakeryFile | None,
        logical_path: LogicalPath,
        plugin_module: str | None,
        preserve_executable: bool = False,
        execution: PluginExecution | None = None,
        custom_package: str | None = None,
        hash_dependency: Path | None = None,
    ) -> None:
        if (content is None) == (hash_dependency is None):
            raise ValueError("A file container needs either content or a hash dependency")
        self.content: Final = content
        self.logical_path: Final = logical_path
        self.plugin_module: Final = plugin_module
        self.preserve_executable: Final = preserve_executable
        self.execution: Final = execution
        self.custom_package: Final = custom_package
        self.hash_dependency: Final = hash_dependency

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"content={self.content!r}, "
            f"logical_path={self.logical_path!r}, "
            f"plugin_module={self.plugin_module!r}, "
            f"preserve_executable={self.preserve_executable!r}, "
            f"execution={self.execution!r}, "
            f"custom_package={self.custom_package!r}, "
            f"hash_dependency={self.hash_dependency!r})"
        )

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @property
    def base_os(self) -> OS | None:
        return None if self.content is None else self.content.base_os

    @property
    def is_plugin(self) -> bool:
        return self.logical_path is LogicalPath.PLUGINS and self.custom_package is None

    def source_path(self, locator: AgentFileLocator) -> Path | None:
        if self.hash_dependency is not None:
            return self.hash_dependency
        return locator.get_source_path(self)

    def relative_source_path(self) -> Path | None:
        """Where the search below the site's agents directories expects the source"""
        if self.content is None or self.content.source is None:
            return None
        if self.custom_package is not None:
            return Path(
                "custom",
                self.custom_package,
                CUSTOM_FILE_SUBDIRS[self.logical_path],
                self.content.source,
            )
        if self.is_plugin:
            return Path("plugins", self.content.source)
        return self.content.source

    def place(
        self,
        pkg_root: Path,
        locator: AgentFileLocator,
        target_location: Path,
        unix_permissions: int,
    ) -> None:
        if self.content is None:
            return
        self.content.place(
            self.source_path(locator),
            pkg_root / self._target_location(target_location),
            unix_permissions,
            self.preserve_executable,
        )

    def _target_location(self, target_location: Path) -> Path:
        # The Unix agents run the plug-ins of a subdirectory named after the
        # cache interval asynchronously.
        if not self.is_plugin or self.base_os is OS.WINDOWS:
            return target_location
        interval = None if self.execution is None else self.execution.interval
        return target_location / str(interval or "")

    def apply_config(self, yml_store: YamlStore) -> None:
        if not self.is_plugin or self.execution is None or self.content is None:
            return
        execution = self.execution
        if not any(
            (execution.asynchronous, execution.interval, execution.timeout, execution.retry_count)
        ):
            return
        entry: dict = {"pattern": "$CUSTOM_PLUGINS_PATH$\\" + str(self.content.target)}
        if execution.asynchronous is not None:
            entry["async"] = execution.asynchronous
        if execution.interval is not None:
            entry["cache_age"] = execution.interval
        if execution.timeout is not None:
            entry["timeout"] = execution.timeout
        if execution.retry_count is not None:
            entry["retry_count"] = execution.retry_count
        yml_store.make_sub_list("plugins", "execution").append(entry)


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
        self.source: Path = source  # type: ignore[mutable-override]
        self._line_mapping = line_mapping or {}

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"source={self.source!r}, "
            f"target={self.target!r}, "
            f"line_mapping={self._line_mapping!r})"
        )

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
    def add_to_line_mapping(self, mapping: Mapping[str, str]) -> None:
        self._line_mapping.update(mapping)

    @override
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

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"lines={self._lines!r}, "
            f"target={self.target!r}, "
            f"include_header={self._include_header!r})"
        )

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
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

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"content={self._content if len(self._content) <= 20 else self._content[:20] + b'...'!r}, "
            f"target={self.target!r})"
        )

    @override
    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    @override
    def _specific_place(self, _source_path: object, target_path: Path) -> None:
        target_path.write_bytes(self._content)
