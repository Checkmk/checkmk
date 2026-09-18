#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Never, Protocol

from cmk.bakery.v2_unstable import (
    Plugin,
    PluginConfig,
    Scriptlet,
    SystemBinary,
    SystemConfig,
    WindowsConfigEntry,
    WindowsConfigItems,
    WindowsGlobalConfigEntry,
    WindowsSystemConfigEntry,
)

from ._artifacts import ScriptletHandle, YamlEntry, YamlItems, YamlPluginSettings
from ._recipes import BinaryFile, CustomFile, HashDependency, SiteFile, TextFile
from ._types import AgentConfig, AgentHash


class CoreFilesFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any
    ) -> Iterator[
        Plugin
        | SystemBinary
        | PluginConfig
        | SystemConfig
        | SiteFile
        | TextFile
        | BinaryFile
        | CustomFile
        | HashDependency
    ]: ...


class CoreScriptletsFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any, aghash: AgentHash
    ) -> Iterator[Scriptlet | ScriptletHandle]: ...


class CoreYamlConfigFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any, aghash: AgentHash
    ) -> Iterator[
        WindowsConfigEntry
        | WindowsGlobalConfigEntry
        | WindowsSystemConfigEntry
        | WindowsConfigItems
        | YamlEntry
        | YamlItems
        | YamlPluginSettings
    ]: ...


def _noop(*_a: object, **_kw: object) -> Iterator[Never]:
    yield from ()


@dataclass(frozen=True, kw_only=True)
class CoreBakelet:
    """A built-in ("core") bakelet, discovered as module-level data.

    Instances are picked up by Checkmk if their variable name starts with
    ``core_bakelet_`` and they live under ``cmk/plugins/<family>/bakery/``.

    Unlike :class:`cmk.bakery.v2.BakeryPlugin`, the functions receive
    keyword arguments dispatched by name (``agconf``, ``conf``, ``aghash``).
    That signature is fixed, so a bakelet which does not need all three
    suppresses ARG001 on the unused ones.

    The functions yield recipes: the artifact types of :mod:`cmk.bakery.v2`
    or the types of this package such as ``SiteFile`` and ``TextFile``. The
    bakery turns them into its file containers, knows the module the bakelet was
    discovered in, and looks sources up in the agents folder of the bakelet's
    plug-in family first. Use the internal types only for what the versioned API
    cannot express.

    ``default_parameters`` are merged underneath the user-provided configuration
    for this bakelet (the user's values win). They are applied during config
    assembly, before the configuration is handed to the bakelet, so a bakelet
    with defaults always receives a configuration even when no rule matched.
    """

    name: str
    files_function: CoreFilesFunction = _noop
    scriptlets_function: CoreScriptletsFunction = _noop
    windows_config_function: CoreYamlConfigFunction = _noop
    default_parameters: Mapping[str, object] | None = None


def entry_point_prefixes() -> Mapping[type[CoreBakelet], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    core_bakelet_... = CoreBakelet(...)
    """
    return {
        CoreBakelet: "core_bakelet_",
    }
