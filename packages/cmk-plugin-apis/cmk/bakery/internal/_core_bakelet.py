#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Never, Protocol

from ._artifacts import (
    AgentInternalFileContainer,
    CustomFileContainer,
    HomeFileContainer,
    LibFileContainer,
    PluginConfigContainer,
    PluginContainer,
    RootFileContainer,
    ScriptletHandle,
    SystemBinaryContainer,
    SystemConfigContainer,
    YamlEntry,
    YamlItems,
    YamlPluginSettings,
)
from ._types import AgentConfig, AgentHash


class CoreFilesFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any
    ) -> Iterator[
        PluginContainer
        | SystemBinaryContainer
        | PluginConfigContainer
        | SystemConfigContainer
        | LibFileContainer
        | AgentInternalFileContainer
        | RootFileContainer
        | HomeFileContainer
        | CustomFileContainer
    ]: ...


class CoreScriptletsFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any, aghash: AgentHash
    ) -> Iterator[ScriptletHandle]: ...


class CoreYamlConfigFunction(Protocol):
    def __call__(
        self, *, agconf: AgentConfig, conf: Any, aghash: AgentHash
    ) -> Iterator[YamlEntry | YamlItems | YamlPluginSettings]: ...


def _noop(*_a: object, **_kw: object) -> Iterator[Never]:
    yield from ()


@dataclass(frozen=True, kw_only=True)
class CoreBakelet:
    """A built-in ("core") bakelet, discovered as module-level data.

    Instances are picked up by Checkmk if their variable name starts with
    ``core_bakelet_`` and they live under ``cmk/plugins/<family>/bakery/``.

    Unlike :class:`cmk.bakery.v2_unstable.BakeryPlugin`, the functions receive
    keyword arguments dispatched by name (``agconf``, ``conf``, ``aghash``) and
    yield the bakery artifact types directly.
    """

    name: str
    files_function: CoreFilesFunction = _noop
    scriptlets_function: CoreScriptletsFunction = _noop
    windows_config_function: CoreYamlConfigFunction = _noop


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
