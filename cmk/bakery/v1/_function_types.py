#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import inspect
import string
from collections.abc import Callable, Iterator, Sequence
from typing import Final, NamedTuple, Self

from ._artifact_types import (
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


class BakeryPluginName:
    # A plug-in name must be a non-empty string consisting only
    # of letters A-z, digits and the underscore.
    VALID_CHARACTERS: Final = string.ascii_letters + "_" + string.digits

    @classmethod
    def _validate_args(cls, /, __str: str) -> str:
        if not isinstance(__str, str):
            raise TypeError(f"{cls.__name__} must initialized from str")
        if not __str:
            raise ValueError(f"{cls.__name__} initializer must not be empty")

        if invalid := "".join(c for c in __str if c not in cls.VALID_CHARACTERS):
            raise ValueError(f"Invalid characters in {__str!r} for {cls.__name__}: {invalid!r}")

        return __str

    def __getnewargs__(self) -> tuple[str]:
        return (str(self),)

    def __new__(cls, /, __str: str) -> Self:
        cls._validate_args(__str)
        return super().__new__(cls)

    def __init__(self, /, __str: str) -> None:
        self._value: Final = __str
        self._hash: Final = hash(type(self).__name__ + self._value)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    def __str__(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(f"cannot compare {self!r} and {other!r}")
        return self._value == other._value

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._value < other._value

    def __le__(self, other: Self) -> bool:
        return self < other or self == other

    def __gt__(self, other: Self) -> bool:
        return not self <= other

    def __ge__(self, other: Self) -> bool:
        return not self < other

    def __hash__(self) -> int:
        return self._hash


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
