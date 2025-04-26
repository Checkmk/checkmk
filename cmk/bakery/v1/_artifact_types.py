#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from pathlib import Path

from ._constants import DebStep, OS, PkgStep, RpmStep, SolStep, WindowsConfigContent


def _validate_type(
    candidate: object,
    expected_type: type,
    name: str,
    *,
    allow_none: bool = False,
) -> None:
    if allow_none and candidate is None:
        return
    if not isinstance(candidate, expected_type):
        raise TypeError(
            f"{name} Argument must be of type {expected_type.__name__}, "
            f"got {type(candidate).__name__}"
        )


def _validate_base_os(base_os: OS) -> None:
    _validate_type(base_os, OS, "base_os")


def _validate_source(source: Path) -> None:
    _validate_type(source, Path, "source")


def _validate_optional_target(target: Path | None) -> None:
    _validate_type(target, Path, "target", allow_none=True)


def _validate_str_list(lines: Iterable[str], name: str) -> None:
    _validate_type(lines, list, name)
    for index, entry in enumerate(lines):
        if not isinstance(entry, str):
            raise TypeError(
                f"Entries of {name} argument must be of type str, got "
                f"{type(entry).__name__} at index {index}"
            )


def _validate_lines(lines: Iterable[str]) -> None:
    _validate_str_list(lines, "lines")


class Plugin:
    """File artifact that represents a Checkmk agent plugin

    The specified plug-in file will be deployed to the Checkmk agent's plug-in directory as
    a callable plugin.

    Args:
        base_os: The target operating system.
        source: Path of the plug-in file, relative to the plug-in source directory on the Checkmk site.
            This usually consists only of the filename.
        target: Target path, relative to the plug-in directory within the agent's file tree
            on the target system. If omitted, the plug-in will be deployed under it's
            relative source path/filename.
        interval: Caching interval in seconds. The plug-in will only be executed by the
            agent after the caching interval is elapsed.
        asynchronous: Relevant for Windows Agent. Don't wait for termination of the plugin's
            process if True. An existent interval will always result in asynchronous execution.
        timeout: Relevant for Windows Agent. Maximum waiting time for a plug-in to terminate.
        retry_count: Relevant for Windows Agent. Maximum number of retried executions after a
            failed plug-in execution.
    """

    def __init__(
        self,
        *,
        base_os: OS,
        source: Path,
        target: Path | None = None,
        interval: int | None = None,
        asynchronous: bool | None = None,
        timeout: int | None = None,
        retry_count: int | None = None,
    ) -> None:
        _validate_base_os(base_os)
        _validate_source(source)
        _validate_optional_target(target)
        _validate_type(interval, int, "interval", allow_none=True)
        _validate_type(asynchronous, bool, "asynchronous", allow_none=True)
        _validate_type(timeout, int, "timeout", allow_none=True)
        _validate_type(retry_count, int, "retry_count", allow_none=True)

        self.base_os = base_os
        self.source = source
        self.target = target
        self.interval = interval
        self.asynchronous = asynchronous
        self.timeout = timeout
        self.retry_count = retry_count

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"source={self.source!r}, "
            f"target={self.target!r}, "
            f"interval={self.interval!r}, "
            f"asynchronous={self.asynchronous!r}, "
            f"timeout={self.timeout!r}, "
            f"retry_count={self.retry_count!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class SystemBinary:
    """File artifact that represents a script/program that should be deployed on the hosts.

    Under UNIX, the file will be deployed to the binary directory (by default, '/usr/bin',
    configurable in WATO).

    Under Windows, the file will be deployed to the 'bin'-folder at the agent's installation directory.

    Args:
        base_os: The target operating system.
        source: Path of the file, relative to the agent source directory on the Checkmk site.
        target: Target path, relative to the binart directory on the target system. If omitted,
            the plug-in will be deployed under it's relative source path/filename.
    """

    def __init__(self, *, base_os: OS, source: Path, target: Path | None = None) -> None:
        _validate_base_os(base_os)
        _validate_source(source)
        _validate_optional_target(target)

        self.base_os = base_os
        self.source = source
        self.target = target

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"source={self.source!r}, "
            f"target={self.target!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class PluginConfig:
    """File artifact that represents a generated config file for a plugin.

    The resulting configuration file will be placed to the agent's config directory (by default,
    '/etc/check_mk', configurable in WATO) and is meant to be read by the corresponding plugin.
    It's content is unrestricted (apart from the fact that it must be passed as a list of 'str's),
    so it's up to the consuming plug-in to process it correctly.

    Args:
        base_os: The target operating system.
        lines: Lines of text that will be printed to the resulting file.
        target: Path of the resulting configuration file, relative to the agent's config
            directory. This usually consists only of the filename.
        include_header: If True, the following header will be prepended at the start of
            the resulting configuration file:

            # Created by Check_MK Agent Bakery.

            # This file is managed via WATO, do not edit manually or you

            # lose your changes next time when you update the agent.
    """

    def __init__(
        self, *, base_os: OS, lines: Iterable[str], target: Path, include_header: bool = False
    ) -> None:
        _validate_base_os(base_os)
        _validate_lines(lines)
        _validate_type(target, Path, "target")
        _validate_type(include_header, bool, "include_header")

        self.base_os = base_os
        self.lines = lines
        self.target = target
        self.include_header = include_header

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"lines={self.lines!r}, "
            f"target={self.target!r}, "
            f"include_header={self.include_header!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class SystemConfig:
    """File artifact that represents a generated configuration file for the target system.

    This is only relevant for UNIX systems.

    The resulting configuration file will be placed under '/etc' on the target system.
    This can be used, for example, to deploy a systemd service or to deploy a config file
    to a service's <service>.d directory.

    Args:
        base_os: The target operating system.
        lines: Lines of text that will be printed to the resulting file.
        target: Path of the resulting configuration file, relative to '/etc'.
        include_header: If True, the following header will be prepended at the start of
            the resulting configuration file:

            # Created by Check_MK Agent Bakery.

            # This file is managed via WATO, do not edit manually or you

            # lose your changes next time when you update the agent.
    """

    def __init__(
        self, *, base_os: OS, lines: list[str], target: Path, include_header: bool = False
    ) -> None:
        _validate_base_os(base_os)
        _validate_lines(lines)
        _validate_type(target, Path, "target")
        _validate_type(include_header, bool, "include_header")

        self.base_os = base_os
        self.lines = lines
        self.target = target
        self.include_header = include_header

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_os={self.base_os!r}, "
            f"lines={self.lines!r}, "
            f"target={self.target!r}, "
            f"include_header={self.include_header!r})"
        )

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class Scriptlet:
    """Represents a 'Scriptlet' (RPM), 'Maintainer script' (DEB) or
    'Installation script' (Solaris PKG)

    Describes a shell script that should be executed at a specific time during a
    package transition, i.e. package installation, update, or uninstallation.
    For a detailed explanation of the meaning and the execution time of the
    steps/scripts, please refer to the documentation of the three packaging
    systems.

    Args:
        step: Takes any Enum of the types 'RpmStep', 'DebStep', 'SolStep', e.g.
            RpmStep.POST for a scriptlet that should be executed right after
            package installation.
        lines: Lines of text that the scriptlet consists of. Don't add a
            shebang line - The executing shell depends on the packaging system.
            Usually, this will be the Bourne shell (sh), so the scriptlets should
            be compatible to that.
    """

    def __init__(self, *, step: PkgStep, lines: list[str]) -> None:
        self._validate_step(step)
        _validate_lines(lines)

        self.step = step
        self.lines = lines

    @staticmethod
    def _validate_step(step):
        expected_types = (RpmStep, DebStep, SolStep)
        if not isinstance(step, expected_types):
            raise TypeError(
                f"step Argument must be of type {sorted([t.__name__ for t in expected_types])}, "
                f"got {type(step).__name__}"
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(step={self.step!r}, lines={self.lines!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


def _validate_windows_config_path(cfg_path: Sequence[str]) -> None:
    _validate_str_list(cfg_path, "path")

    length = len(cfg_path)
    if length < 2:
        raise ValueError(
            "Minimum path length for Windows configuration entry is 2 (i.e. section/name), "
            f"got a length of {length}"
        )
    if length > 3:
        raise ValueError(
            "Maximum path length for Windows configuration entry is 3 (i.e. section/subsection/name), "
            f"got a length of {length})"
        )


def _validate_windows_config_content(content: WindowsConfigContent) -> None:
    expected_types = (int, str, bool, dict, list)
    if not isinstance(content, expected_types):
        raise TypeError(
            "content for Windows Config must be of "
            f"type {sorted([t.__name__ for t in expected_types])}. "
            f"Got {type(content).__name__}."
        )


class WindowsConfigEntry:
    """Config Entry for the Windows Agent yaml file (check_mk.install.yml)

    It's up to the consuming plug-in to read the config entry correctly from the
    yaml file. However, unlike the approach via PluginConfig, config entries described
    here will be accessible consistently via the python yaml module.

    The logical structure of the yaml tree has up to two levels. It is divided into
    sections, that are again divided into subsections.

    A config entry can be inserted to a section or a subsection.

    Args:
        path: The path to the entry consists either of ['section', 'subsection', 'name'] or
            ['section', 'name'], i.e. the resulting list must contain 2 or 3 entries. If the
            path already exists in the yaml structure, it will be overwritten.
        content: The actual content of the config entry. Allowed types are int, str, bool,
            dict, list. Must not contain any complex data types or custom classes.
            (Must be serializable with yaml.safe_dump)

    """

    def __init__(self, *, path: list[str], content: WindowsConfigContent) -> None:
        _validate_windows_config_path(path)
        _validate_windows_config_content(content)

        self.path = path
        self.content = content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r}, content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class WindowsConfigItems:
    """List of entries for the Windows Agent yaml file (check_mk.install.yml)

    This artifact describes a list of entries that is identified by a path
    (section,[ subsection,] name). In contrast to a WindowsConfigEntry, the
    given list will be merged to an already existing list.

    Args:
        path: The path to the entry consists either of ['section', 'subsection', 'name'] or
            ['section', 'name'], i.e. the resulting list must contain 2 or 3 entries. If the
            path already exists in the yaml structure, it will be overwritten.
        content: The list that should be added or merged to the given path. Allowed list
            entries are the same as for WindowsConfigEntry content.
    """

    def __init__(self, *, path: list[str], content: list[WindowsConfigContent]) -> None:
        _validate_windows_config_path(path)
        self._validate_content(content)

        self.path = path
        self.content = content

    @staticmethod
    def _validate_content(content: Sequence[WindowsConfigContent]) -> None:
        _validate_type(content, list, "content")
        for index, entry in enumerate(content):
            try:
                _validate_windows_config_content(entry)
            except TypeError as te:
                raise TypeError(f"At index {index} of content argument: {te}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path!r}, content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class WindowsGlobalConfigEntry:
    """Shortcut for WindowsConfigEntry(path=['global', name], content=content)

    For details about the 'global' section and it's meaning, please refer to
    the Windows Agent documentation.

    Args:
        name: The name part of the ['global',name] path
        content: The content, according to the WindowsConfigEntry requirements.
    """

    def __init__(self, *, name: str, content: WindowsConfigContent) -> None:
        _validate_type(name, str, "name")
        _validate_windows_config_content(content)

        self.name = name
        self.content = content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__


class WindowsSystemConfigEntry:
    """Shortcut for WindowsConfigEntry(path=['system', name], content=content)

    For details about the 'system' section and it's meaning, please refer to
    the Windows Agent documentation.

    Args:
        name: The name part of the ['global',name] path
        content: The content, according to the WindowsConfigEntry requirements.
    """

    def __init__(self, *, name: str, content: WindowsConfigContent) -> None:
        _validate_type(name, str, "name")
        _validate_windows_config_content(content)

        self.name = name
        self.content = content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, content={self.content!r})"

    def __eq__(self, other: object) -> bool:
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__
