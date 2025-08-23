#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import string
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Final, Never

from ..v1._artifact_types import (
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

_VALID_CHARACTERS: Final = string.ascii_letters + "_" + string.digits


def _parse_valid_plugin_name(name: str) -> str:
    """Parse a valid plugin name.

    A valid plugin name must be a non-empty string consisting only
    of letters A-z, digits and the underscore.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    if not name:
        raise ValueError("name must not be empty")

    if invalid := "".join(c for c in name if c not in _VALID_CHARACTERS):
        raise ValueError(f"Invalid characters in {name!r}: {invalid!r}")

    return name


def no_op_parser(
    parameters: Mapping[str, object],
) -> Mapping[str, object]:
    """A no-op parser that does nothing and passes the parameters through.

    Use this if you insist on not using a parser at all.
    """
    return parameters


def _nothing(conf: object) -> Iterable[Never]:
    return ()


@dataclass
class BakeryPlugin[ConfigType]:
    """
    Defines a bakery plugin

    Instances of this class will only be picked up by Checkmk if their names start with
    ``bakery_plugin_``.

    Args:
        name: Bakery plugin name.
            A valid plugin name must be a non-empty string consisting only
            of letters A-z, digits and the underscore.

    """

    name: str
    parameter_parser: Callable[[Mapping[str, object]], ConfigType]
    files_function: Callable[
        [ConfigType], Iterable[Plugin | PluginConfig | SystemBinary | SystemConfig]
    ] = _nothing
    scriptlets_function: Callable[[ConfigType], Iterable[Scriptlet]] = _nothing
    windows_config_function: Callable[
        [ConfigType],
        Iterable[
            WindowsConfigEntry
            | WindowsGlobalConfigEntry
            | WindowsSystemConfigEntry
            | WindowsConfigItems
        ],
    ] = _nothing

    def __post_init__(self) -> None:
        self.name = _parse_valid_plugin_name(self.name)


def entry_point_prefixes() -> Mapping[type[BakeryPlugin], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    bakery_plugin_... = BakeryPlugin(...)
    """
    return {
        BakeryPlugin: "bakery_plugin_",
    }
