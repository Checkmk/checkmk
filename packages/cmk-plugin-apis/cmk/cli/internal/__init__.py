#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Internal CLI API: the ``Command`` plug-in type, its option declarations and the discovery prefix.

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
from functools import partial
from pathlib import Path
from typing import Protocol


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
class _OptionDeclaration:
    long: str
    help: str
    short: str | None = None
    deprecated_names: frozenset[str] = frozenset()


@dataclass(frozen=True, kw_only=True)
class Flag(_OptionDeclaration):
    """An option without argument: reading it tells whether it was given"""


@dataclass(frozen=True, kw_only=True)
class Count(_OptionDeclaration):
    """An option without argument: reading it counts how often it was given"""


@dataclass(frozen=True, kw_only=True)
class Value[T](_OptionDeclaration):
    """An option with an argument: reading it parses the last argument given"""

    placeholder: str
    """What the help shows in place of the argument, e.g. ``"N"``"""
    parse: Callable[[str], T]
    """Parses the argument; a ``ValueError`` rejects the command line"""


@dataclass(frozen=True, kw_only=True)
class Values[T](_OptionDeclaration):
    """An option with an argument, given any number of times: reading it parses every argument"""

    placeholder: str
    """What the help shows in place of the argument, e.g. ``"N"``"""
    parse: Callable[[str], T]
    """Parses each argument; a ``ValueError`` rejects the command line"""


class Reader(Protocol):
    """Reads a command's options by their declarations, each with its declared type"""

    def flag(self, option: Flag) -> bool: ...

    def count(self, option: Count) -> int: ...

    def value[T](self, option: Value[T]) -> T | None: ...

    def values[T](self, option: Values[T]) -> Sequence[T]: ...


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


def _read_option(reader: Reader, option: Option) -> object | None:
    match option.argument:
        case None if option.repeat:
            return (
                reader.count(
                    Count(
                        long=option.long,
                        help=option.help,
                        short=option.short,
                        deprecated_names=option.deprecated_names,
                    )
                )
                or None
            )
        case None:
            given = reader.flag(
                Flag(
                    long=option.long,
                    help=option.help,
                    short=option.short,
                    deprecated_names=option.deprecated_names,
                )
            )
            return True if given else None
        case str() as argument if option.repeat:
            return (
                tuple(
                    reader.values(
                        Values(
                            long=option.long,
                            help=option.help,
                            short=option.short,
                            deprecated_names=option.deprecated_names,
                            placeholder=argument,
                            parse=option.parse or str,
                        )
                    )
                )
                or None
            )
        case str() as argument:
            return reader.value(
                Value(
                    long=option.long,
                    help=option.help,
                    short=option.short,
                    deprecated_names=option.deprecated_names,
                    placeholder=argument,
                    parse=option.parse or str,
                )
            )


def _read_options(sub_options: Sequence[Option], reader: Reader) -> Options:
    return {
        option.long: value
        for option in sub_options
        if (value := _read_option(reader, option)) is not None
    }


def untyped_request(sub_options: Sequence[Option] = ()) -> Callable[[Reader], Options]:
    """The request of a command whose handler reads its options from the untyped mapping"""
    return partial(_read_options, sub_options)


@dataclass(frozen=True, kw_only=True)
class Command[R]:
    """A command of the ``cmk`` command line, selected via ``--<long>``.

    A command declares its options by reading them in its request function,
    which assembles the request its handler receives:

    >>> from dataclasses import dataclass
    >>> @dataclass(frozen=True, kw_only=True)
    ... class GreetRequest:
    ...     loud: bool
    ...     times: int | None
    >>> def greet_request(options: Reader) -> GreetRequest:
    ...     return GreetRequest(
    ...         loud=options.flag(Flag(long="loud", help="Shout")),
    ...         times=options.value(
    ...             Value(long="times", help="Repeat", placeholder="N", parse=int)
    ...         ),
    ...     )
    >>> def greet(context: Context, request: GreetRequest, args: Args) -> ExitCode:
    ...     greeting = "HELLO" if request.loud else "Hello"
    ...     print(greeting, ", ".join(args))
    ...     return ExitCode.SUCCESS
    >>> cli_command_greet = Command(
    ...     name="greet",
    ...     long="greet",
    ...     request=greet_request,
    ...     handler=greet,
    ...     help="Greet the given names",
    ...     arguments=Arguments("NAME...", optional=True),
    ... )

    A request function only reads and assembles: the engine runs it once with
    a reader that records the declarations, so an option read conditionally
    would be missing from the help. Checks across options belong in the handler.
    """

    name: str
    """The name under which the command is registered, a Python identifier"""
    long: str
    """The long option that selects the command"""
    help: str
    request: Callable[[Reader], R]
    """Reads the command's options and assembles its request.

    The engine calls it once with a reader that only records the declarations,
    to learn which options the command has, and once per run with the parsed
    command line.
    """
    handler: Callable[[Context, R, Args], ExitCode]
    """Runs the command with its request and returns the exit status"""
    short: str | None = None
    arguments: Arguments | None = None
    description: Sequence[str] | None = None

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"{self.name!r} is not an identifier")


def entry_point_prefixes() -> Mapping[type[Command[object]], str]:
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
    "Count",
    "entry_point_prefixes",
    "ExitCode",
    "Flag",
    "GlobalOptions",
    "Reader",
    "Options",
    "untyped_request",
    "Value",
    "Values",
]
