#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import inspect
from collections.abc import Callable, Iterator, Sequence
from typing import NamedTuple

from cmk.utils.validatedstr import ValidatedString

from .artifact_types import (
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

FileReturnType = Plugin | SystemBinary | PluginConfig | SystemConfig
FileGenerator = Iterator[FileReturnType]
"""Return type for the 'files_function' generator function."""

ScriptletReturnType = Scriptlet
ScriptletGenerator = Iterator[ScriptletReturnType]
"""Return type for the 'scriptlets_function' generator function."""

WindowsConfigReturnType = (
    WindowsConfigEntry | WindowsConfigItems | WindowsGlobalConfigEntry | WindowsSystemConfigEntry
)
WindowsConfigGenerator = Iterator[WindowsConfigReturnType]
"""Return type for the 'windows_config_function' generator function."""

FilesFunction = Callable[..., FileGenerator]
ScriptletsFunction = Callable[..., ScriptletGenerator]
WindowsConfigFunction = Callable[..., WindowsConfigGenerator]

_PossibleReturnType = FileReturnType | ScriptletReturnType | WindowsConfigReturnType
# NOTE: Union is used because of bug https://github.com/python/mypy/issues/12393
_PossibleFunctionType = FilesFunction | ScriptletsFunction | WindowsConfigFunction


class BakeryPluginName(ValidatedString):
    pass


class BakeryPlugin(NamedTuple):
    name: BakeryPluginName
    files_function: FilesFunction
    scriptlets_function: ScriptletsFunction
    windows_config_function: WindowsConfigFunction


def _validate_function(
    function: _PossibleFunctionType | None, function_name: str, allowed_args: Sequence[str]
) -> None:
    if function is None:
        return

    if not inspect.isgeneratorfunction(function):
        raise TypeError(f"{function_name} must be a generator function.")

    function_args = set(inspect.signature(function).parameters)

    if not_allowed := function_args.difference(set(allowed_args)):
        raise ValueError(f"Unsupported argument(s) {not_allowed} in definition of {function_name}.")


def _noop_files_function() -> FileGenerator:
    yield from ()


def _noop_scriptlets_function() -> ScriptletGenerator:
    yield from ()


def _noop_windows_config_function() -> WindowsConfigGenerator:
    yield from ()


def _get_function_filter(
    function: _PossibleFunctionType,
    function_name: str,
    test_types: Sequence[type],
) -> Callable:
    def filtered_generator(*args: str, **kwargs: str) -> Iterator[_PossibleReturnType]:
        for element in function(*args, **kwargs):
            _validate_type(function_name, element, test_types)
            yield element

    return filtered_generator


def _validate_type(
    function_name: str, element: _PossibleReturnType, test_types: Sequence[type]
) -> None:
    if isinstance(element, tuple(test_types)):
        return None
    article = " one of" if len(test_types) > 1 else ""
    raise TypeError(
        f"{function_name} yields item of unexpected type: Need{article} "
        f"{', '.join([t.__name__ for t in test_types])}, got {type(element).__name__}"
    )


def _filter_files_function(function: FilesFunction | None) -> FilesFunction:
    if function is None:
        return _noop_files_function
    filtered_function = _get_function_filter(
        function, "files_function", [Plugin, PluginConfig, SystemBinary, SystemConfig]
    )
    return functools.wraps(function)(filtered_function)


def _filter_scriptlets_function(function: ScriptletsFunction | None) -> ScriptletsFunction:
    if function is None:
        return _noop_scriptlets_function
    filtered_function = _get_function_filter(function, "scriptlets_function", [Scriptlet])
    return functools.wraps(function)(filtered_function)


def _filter_windows_config_function(
    function: WindowsConfigFunction | None,
) -> WindowsConfigFunction:
    if function is None:
        return _noop_windows_config_function
    filtered_function = _get_function_filter(
        function,
        "windows_config_function",
        [
            WindowsConfigEntry,
            WindowsConfigItems,
            WindowsGlobalConfigEntry,
            WindowsSystemConfigEntry,
        ],
    )
    return functools.wraps(function)(filtered_function)


def create_bakery_plugin(
    *,
    name: str,
    files_function: FilesFunction | None = None,
    scriptlets_function: ScriptletsFunction | None = None,
    windows_config_function: WindowsConfigFunction | None = None,
) -> BakeryPlugin:
    _validate_function(files_function, "files_function", ["conf"])
    _validate_function(scriptlets_function, "scriptlets_function", ["conf", "aghash"])
    _validate_function(windows_config_function, "windows_config_function", ["conf", "aghash"])

    return BakeryPlugin(
        BakeryPluginName(name),
        _filter_files_function(files_function),
        _filter_scriptlets_function(scriptlets_function),
        _filter_windows_config_function(windows_config_function),
    )
