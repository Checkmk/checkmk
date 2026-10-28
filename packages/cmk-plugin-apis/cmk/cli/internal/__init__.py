#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal CLI API: the ``Command`` plug-in type, its ``Option`` and the discovery prefix.

This is the ``internal`` variant of the per-domain command line API (see the
plugin discovery reference in ``cmk.discover_plugins``). It is not exposed to
third-party plug-in authors; it carries the commands (historically "modes")
the ``cmk`` command offers, e.g. ``cmk --check``.

To be discovered, a plug-in module must be placed in the ``cli`` subdirectory of a
plug-in family (``cmk/plugins/<family>/cli/<module>.py``) and the plug-in instance
name must start with the prefix returned by :func:`entry_point_prefixes`.
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ExitCode(Enum):
    """The exit codes the engine and the command handlers report"""

    SUCCESS = 0
    FAILURE = 1
    """Any failure not reported otherwise, e.g. a crashed command"""
    ERROR = 2
    """A command's own error, e.g. the monitoring plug-in API's CRITICAL state or an automation's unknown error"""
    UNKNOWN = 3
    """The command refused its command line or input: an invalid option, an unknown
    host, a missing file. The number is the monitoring plug-in API's UNKNOWN state,
    so a check invoked wrongly reports UNKNOWN rather than WARNING (1) or CRITICAL (2).
    """
    INTERRUPTED = 130
    """128 + SIGINT, as a shell reports a command interrupted by Ctrl-C"""
    BROKEN_PIPE = 141
    """128 + SIGPIPE, as a shell reports a command whose reader went away"""


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
    (log level, profiling) before the command's handler runs. The handler
    receives the values for whatever it has to do with them itself, such as
    switching on debug mode for the Checkmk code it reaches.
    """

    verbosity: int = 0
    """The number of ``-v`` / ``--verbose`` occurrences"""
    debug: bool = False
    """``--debug``: let most Python exceptions raise through"""
    profile: bool = False
    """``--profile``: profile the command"""


@dataclass(frozen=True, kw_only=True)
class Context:
    """What the engine hands every command besides its own options and arguments.

    A command that needs more of the runtime than that builds it itself, e.g.
    with ``cmk.base.app.make_app()``.
    """

    omd_root: Path
    """The site's root directory"""
    global_options: GlobalOptions
    logger: logging.Logger
    """Where the command reports what the engine would report, e.g. its errors"""


type CommandHandler = Callable[[Context, Options, Args], ExitCode]
"""The signature of a command's handler; it returns the exit status."""


@dataclass(frozen=True)
class Arguments:
    """The positional arguments of a :class:`Command`"""

    placeholder: str
    """What the help shows in their place, e.g. ``"HOST"`` or ``"HOST1 HOST2..."``"""
    optional: bool = False
    """Whether the command takes any number of arguments, none included, instead of exactly one"""


@dataclass(frozen=True, kw_only=True)
class Option:
    """A sub-option of a :class:`Command`, handed to the command's handler as part of its options.

    An option can either
    a) have an argument (with ``repeat``, every value is collected),
    b) have no argument and count its occurrences (``repeat``), or
    c) have no argument (its presence is passed as ``True``).
    """

    long: str
    help: str
    short: str | None = None
    argument: str | None = None
    """What the help shows in the argument's place; ``None`` for an option without argument"""
    parse: Callable[[str], object] | None = None
    argument_optional: bool = False
    repeat: bool = False
    deprecated_names: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.argument is None and (self.parse is not None or self.argument_optional):
            raise ValueError(f"--{self.long} parses or makes optional an argument it does not take")


@dataclass(frozen=True, kw_only=True)
class Command:
    """A command of the ``cmk`` command line, selected via ``--<long>``.

    Example:
    ********

    >>> def greet(context: Context, options: Options, args: Args) -> ExitCode:
    ...     print("Hello", ", ".join(args))
    ...     return ExitCode.SUCCESS
    >>> cli_command_greet = Command(
    ...     name="greet",
    ...     long="greet",
    ...     handler_function=greet,
    ...     help="Greet the given names",
    ...     arguments=Arguments("NAME...", optional=True),
    ... )
    """

    name: str
    """The name under which the command is registered, a Python identifier"""
    long: str
    """The long option that selects the command"""
    handler_function: CommandHandler
    help: str
    short: str | None = None
    arguments: Arguments | None = None
    description: Sequence[str] | None = None
    sub_options: Sequence[Option] = ()

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"{self.name!r} is not an identifier")


def entry_point_prefixes() -> Mapping[type[Command], str]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    cli_command_... = Command(...)
    """
    return {Command: "cli_command_"}


__all__ = [
    "Args",
    "Arguments",
    "Command",
    "Option",
    "Context",
    "CommandHandler",
    "entry_point_prefixes",
    "ExitCode",
    "GlobalOptions",
    "Options",
]
