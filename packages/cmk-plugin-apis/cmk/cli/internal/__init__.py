#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal CLI API: the ``CLICommand`` plug-in type, its ``CLIOption`` and the discovery prefix.

This is the ``internal`` variant of the per-domain command line API (see the
plugin discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the commands (historically "modes")
the ``cmk`` command offers, e.g. ``cmk --check``.

To be discovered, a plug-in module must be placed in the ``cli`` subdirectory of a
plug-in family (``cmk/plugins/<family>/cli/<module>.py``) and the plug-in instance
name must start with the prefix returned by :func:`entry_point_prefixes`.
"""

# The application object handed to every command is not typed yet (see BaseApp).
# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

type BaseApp = Any  # FIXME: the application object's type lives in cmk.base for now

type Options = Mapping[str, object]
"""The parsed sub-options of a command, keyed by their long option name.

A flag is ``True``, a repeated flag its count, an option with an argument its
(converted) argument, a repeated one a tuple of all its arguments.
"""

type Args = Sequence[str]
"""The positional arguments of a command.

Empty for commands without an argument, exactly one element for commands with a
required argument, and all remaining command line arguments for commands with an
optional argument.
"""


@dataclass(frozen=True, kw_only=True)
class GlobalOptions:
    """The options every command accepts.

    The engine declares and parses them, and applies the effects that are its own
    (log level, debug mode, profiling) before the command's handler runs. The
    handler receives the values for whatever it has to do with them itself.
    """

    verbosity: int = 0
    """The number of ``-v`` / ``--verbose`` occurrences"""
    debug: bool = False
    """``--debug``: let most Python exceptions raise through"""
    profile: bool = False
    """``--profile``: profile the command"""
    fake_dns: str | None = None
    """``--fake-dns IP``: use this address for all hosts instead of looking them up

    A plain string: the address type lives in cmk-ccc, on which this package must
    not depend. The handler that uses it validates it.
    """


type CommandHandler = Callable[[BaseApp, GlobalOptions, Options, Args], int]
"""The signature of a command's handler; it returns the exit status."""


def _validate_argument_declaration(
    *,
    argument: bool,
    argument_descr: str | None,
    argument_optional: bool,
    argument_conv: Callable[[str], object] | None = None,
) -> None:
    if (argument_descr is not None) != argument:
        raise ValueError("an argument description is required if and only if there is an argument")
    if argument_conv is not None and not argument:
        raise ValueError("a conversion function requires an argument")
    if argument_optional and not argument:
        raise ValueError("an optional argument requires an argument")


@dataclass(frozen=True, kw_only=True)
class CLIOption:
    """A sub-option of a :class:`CLICommand`, handed to the command's handler as part of its options.

    An option can either
    a) have an argument (with ``repeat``, every value is collected),
    b) have no argument and count its occurrences (``repeat``), or
    c) have no argument (its presence is passed as ``True``).
    """

    long_option: str
    short_help: str
    short_option: str | None = None
    argument: bool = False
    argument_descr: str | None = None
    argument_conv: Callable[[str], object] | None = None
    argument_optional: bool = False
    repeat: bool = False
    deprecated_long_options: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_argument_declaration(
            argument=self.argument,
            argument_descr=self.argument_descr,
            argument_conv=self.argument_conv,
            argument_optional=self.argument_optional,
        )


@dataclass(frozen=True, kw_only=True)
class CLICommand:
    """A command of the ``cmk`` command line, selected via ``--<long_option>``.

    Example:
    ********

    >>> def greet(app: BaseApp, global_options: GlobalOptions, options: Options, args: Args) -> int:
    ...     print("Hello", ", ".join(args))
    ...     return 0
    >>> mode_greet = CLICommand(
    ...     long_option="greet",
    ...     handler_function=greet,
    ...     short_help="Greet the given names",
    ...     argument=True,
    ...     argument_descr="NAME...",
    ...     argument_optional=True,
    ... )
    """

    long_option: str
    handler_function: CommandHandler
    short_help: str
    short_option: str | None = None
    argument: bool = False
    argument_descr: str | None = None
    argument_optional: bool = False
    long_help: Sequence[str] | None = None
    sub_options: Sequence[CLIOption] = ()

    @property
    def name(self) -> str:
        """The name under which the command is registered: its long option"""
        return self.long_option

    def __post_init__(self) -> None:
        _validate_argument_declaration(
            argument=self.argument,
            argument_descr=self.argument_descr,
            argument_optional=self.argument_optional,
        )


def entry_point_prefixes() -> Mapping[type[CLICommand], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    cli_command_... = CLICommand(...)
    """
    return {CLICommand: "cli_command_"}


__all__ = [
    "Args",
    "BaseApp",
    "CLICommand",
    "CLIOption",
    "CommandHandler",
    "entry_point_prefixes",
    "GlobalOptions",
    "Options",
]
