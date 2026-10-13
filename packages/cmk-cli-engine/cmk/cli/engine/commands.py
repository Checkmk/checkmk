#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import shlex
import signal
import subprocess
import sys
import textwrap
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from typing import Final, override

from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.internal import (
    CLICommand,
    CLIOption,
    CommandHandler,
    entry_point_prefixes,
    GlobalOptions,
)
from cmk.discover_plugins import discover_all_plugins, PluginGroup

OptionSpec = str
Argument = str
OptionName = str
ConvertFunction = Callable[[str], object]
Options = list[tuple[OptionSpec, Argument]]
Arguments = Sequence[str]


def write_stdout(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


class Option:
    def __init__(
        self,
        *,
        long_option: str,
        short_help: str,
        short_option: str | None = None,
        # ----------------------------------------------------------------------
        # TODO: To avoid nonsensical and/or contradicting value combinations,
        # all these argument-related parameters below should actually be a
        # *single* parameter, see their intrinsic relations below.
        argument: bool = False,
        argument_descr: str | None = None,
        argument_conv: ConvertFunction | None = None,
        argument_optional: bool = False,
        repeat: bool = False,
        # ----------------------------------------------------------------------
        deprecated_long_options: set[str] | None = None,
    ) -> None:
        super().__init__()

        # We have an argument description if and only if we have an argument.
        assert (argument_descr is not None) == argument
        # Having a conversion function implies that we have an argument.
        assert (argument_conv is None) or argument
        # Being optional implies that we actually have an argument.
        assert not argument_optional or argument

        self.long_option = long_option
        self.short_help = short_help
        self.short_option = short_option
        self._deprecated_long_options = deprecated_long_options or set()

        self.repeat = repeat
        self.argument = argument
        self.argument_descr = argument_descr
        self.argument_conv = argument_conv
        self.argument_optional = argument_optional

    @property
    def name(self) -> str:
        return self.long_option

    def options(self) -> list[str]:
        options = []
        if self.short_option:
            options.append(f"-{self.short_option}")
        options.append(f"--{self.long_option}")
        options.extend(f"--{opt}" for opt in self._deprecated_long_options)
        return options

    def is_deprecated_option(self, opt_str: str) -> bool:
        return opt_str.lstrip("-") in self._deprecated_long_options

    def short_help_text(self, fmt: str) -> str:
        option_txt = " %s" % (", ".join(self.options()))

        if self.argument:
            option_txt += " "
            descr = self.argument_descr if self.argument_descr else "..."
            if self.argument_optional:
                option_txt += "[%s]" % descr
            else:
                option_txt += descr

        formated_option_txt = fmt % option_txt

        wrapper = textwrap.TextWrapper(
            initial_indent=formated_option_txt,
            subsequent_indent=" " * len(fmt % ""),
            width=80,
        )
        return wrapper.fill(self.short_help)

    def short_getopt_specs(self) -> list[str]:
        if (spec := self.short_option) is None:
            return []
        if self.argument and not self.argument_optional:
            spec += ":"
        return [spec]

    def long_getopt_specs(self) -> list[str]:
        specs = [self.long_option]
        specs.extend(self._deprecated_long_options)
        if self.argument and not self.argument_optional:
            return [f"{spec}=" for spec in specs]
        return specs


def parse_sub_options(
    sub_options: Sequence[Option], all_opts: Options
) -> Mapping[OptionName, object]:
    options: dict[OptionName, object] = {}
    counts: Counter[OptionName] = Counter()
    collected: dict[OptionName, list[Argument]] = {}

    for o, a in all_opts:
        for option in sub_options:
            if o not in option.options():
                continue

            if option.is_deprecated_option(o):
                write_stdout(
                    tty.format_warning(f"{o!r} is deprecated in favour of option {option.name!r}")
                    + "\n"
                )

            if a and not option.argument:
                raise MKGeneralException("No argument to %s expected." % o)

            if option.repeat:
                if option.argument:
                    collected.setdefault(option.name, []).append(a)
                else:
                    counts[option.name] += 1
                continue

            val: object = a
            if not option.argument:
                val = True
            elif option.argument_conv:
                try:
                    val = option.argument_conv(a)
                except ValueError:
                    raise MKGeneralException("%s: Invalid argument" % o)

            options[option.name] = val

    return {
        **options,
        **counts,
        **{name: tuple(values) for name, values in collected.items()},
    }


def option_string(parsed: Mapping[OptionName, object], name: OptionName) -> str | None:
    match parsed.get(name):
        case None:
            return None
        case str() as value:
            return value
        case value:
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")


def option_strings(parsed: Mapping[OptionName, object], name: OptionName) -> Sequence[str]:
    match parsed.get(name):
        case None:
            return ()
        case tuple() as value:
            strings = tuple(element for element in value if isinstance(element, str))
            if len(strings) == len(value):
                return strings
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")
        case value:
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")


def option_count(parsed: Mapping[OptionName, object], name: OptionName) -> int:
    match parsed.get(name):
        case int() as value:
            return value
        case value:
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")


def option_names[NameT](
    parsed: Mapping[OptionName, object], name: OptionName, type_: type[NameT]
) -> frozenset[NameT]:
    match parsed.get(name):
        case set() | frozenset() as value:
            names = frozenset(element for element in value if isinstance(element, type_))
            if len(names) == len(value):
                return names
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")
        case value:
            raise MKGeneralException(f"--{name}: invalid argument {value!r}")


class Command(Option):
    def __init__(
        self,
        *,
        long_option: OptionName,
        handler_function: CommandHandler,
        short_help: str,
        short_option: OptionName | None = None,
        argument: bool = False,
        argument_descr: str | None = None,
        argument_optional: bool = False,
        long_help: list[str] | None = None,
        sub_options: Sequence[Option] = (),
    ) -> None:
        super().__init__(
            long_option=long_option,
            short_help=short_help,
            short_option=short_option,
            argument=argument,
            argument_descr=argument_descr,
            argument_optional=argument_optional,
        )
        self.handler_function = handler_function
        self.long_help = long_help
        self.sub_options = sub_options

    @override
    def short_getopt_specs(self) -> list[str]:
        specs = super().short_getopt_specs()
        for option in self.sub_options:
            specs += option.short_getopt_specs()
        return specs

    @override
    def long_getopt_specs(self) -> list[str]:
        specs = super().long_getopt_specs()
        for option in self.sub_options:
            specs += option.long_getopt_specs()
        return specs

    # expected format is like this
    #  -i, --inventory does a HW/SW Inventory for all, one or several
    #  hosts. If you add the option -f, --force then persisted sections
    #  will be used even if they are outdated.
    def long_help_text(self) -> str | None:
        if not self.long_help and not self.sub_options:
            return None

        text: list[str] = []

        option_text = "  "
        if self.short_option:
            option_text += "-%s, " % self.short_option
        option_text += "--%s " % self.long_option

        if not self.long_help:
            text.append(option_text)
        else:
            for index, paragraph in enumerate(self.long_help):
                initial_indent = option_text if index == 0 else "    "

                wrapper = textwrap.TextWrapper(
                    initial_indent=initial_indent,
                    subsequent_indent="    ",
                    width=80,
                )
                text.append(wrapper.fill(paragraph))

        if self.sub_options:
            sub_texts = [option.short_help_text(fmt="    %-24s") for option in self.sub_options]
            text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

        return "\n\n".join(text)


def make_option(option: CLIOption) -> Option:
    """Build the engine's option from its API declaration"""
    return Option(
        long_option=option.long_option,
        short_help=option.short_help,
        short_option=option.short_option,
        argument=option.argument,
        argument_descr=option.argument_descr,
        argument_conv=option.argument_conv,
        argument_optional=option.argument_optional,
        repeat=option.repeat,
        deprecated_long_options=set(option.deprecated_long_options),
    )


def make_command(command: CLICommand) -> Command:
    """Build the engine's command from its API declaration"""
    return Command(
        long_option=command.long_option,
        handler_function=command.handler_function,
        short_help=command.short_help,
        short_option=command.short_option,
        argument=command.argument,
        argument_descr=command.argument_descr,
        argument_optional=command.argument_optional,
        long_help=list(command.long_help) if command.long_help is not None else None,
        sub_options=[make_option(option) for option in command.sub_options],
    )


_VERBOSE_OPTION = Option(
    long_option="verbose",
    short_option="v",
    short_help="Enable verbose output (Use twice for more)",
)

_DEBUG_OPTION = Option(
    long_option="debug",
    short_help="Let most Python exceptions raise through",
)

_PROFILE_OPTION = Option(
    long_option="profile",
    short_help="Enable profiling mode",
)

_FAKE_DNS_OPTION = Option(
    long_option="fake-dns",
    short_help="Fake IP addresses of all hosts to be IP. This prevents DNS lookups.",
    argument=True,
    argument_descr="IP",
)


def general_options() -> Sequence[Option]:
    """The options every command accepts, see `cmk.cli.internal.GlobalOptions`"""
    return [_VERBOSE_OPTION, _DEBUG_OPTION, _PROFILE_OPTION, _FAKE_DNS_OPTION]


def parse_general_options(all_opts: Options) -> GlobalOptions:
    """Collect the general options from the parsed command line"""
    verbosity = 0
    debug = False
    profile = False
    fake_dns: str | None = None
    for option, argument in all_opts:
        if option in _VERBOSE_OPTION.options():
            verbosity += 1
        elif option in _DEBUG_OPTION.options():
            debug = True
        elif option in _PROFILE_OPTION.options():
            profile = True
        elif option in _FAKE_DNS_OPTION.options():
            fake_dns = argument
    return GlobalOptions(verbosity=verbosity, debug=debug, profile=profile, fake_dns=fake_dns)


def discover_commands() -> Sequence[Command]:
    discovered = discover_all_plugins(
        PluginGroup.CLI,
        entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=True,
    )
    return tuple(make_command(command) for command in discovered.plugins.values())


_DEFAULT_PAGER: Final = "less"

_PAGER_PROMPT: Final = (
    "?ltline %lt?L/%L.:byte %bB?s/%s..?e (END):?pB %pB\\%.. (press h for help or q to quit)"
)

_LESS_OPTIONS: Final = f"--no-init --quit-if-one-screen --prompt={_PAGER_PROMPT}$"


def _pager_environment(environ: Mapping[str, str]) -> Mapping[str, str]:
    return {**environ, "LESS": f"{_LESS_OPTIONS} {environ.get('LESS', '')}".rstrip()}


@contextmanager
def _sigint_ignored() -> Iterator[None]:
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def write_paged(txt: str) -> None:
    if not sys.stdout.isatty():
        write_stdout(txt)
        return

    try:
        with suppress(BrokenPipeError), _sigint_ignored():
            subprocess.run(
                shlex.split(os.environ.get("PAGER") or _DEFAULT_PAGER),
                input=txt,
                text=True,
                check=False,
                env=_pager_environment(os.environ),
            )
    except OSError, ValueError:
        write_stdout(txt)


HELP_OPTION: Final = Option(long_option="help", short_option="h", short_help="Print this help")


def _map_options(commands: Sequence[Command]) -> Mapping[OptionName, Command]:
    """Map every spelling of every command to it, rejecting a collision.

    Two commands claiming the same option would otherwise shadow one another
    silently, and the one that loses simply could not be invoked.
    """
    reserved = {HELP_OPTION.long_option, HELP_OPTION.short_option}
    mapped: dict[OptionName, Command] = {}
    for command in commands:
        for name in (command.long_option, command.short_option):
            if name is None:
                continue
            if name in reserved:
                raise MKGeneralException(f"{name!r} is the help, not the command {command.name!r}")
            if (other := mapped.get(name)) is not None:
                raise MKGeneralException(
                    f"{name!r} is claimed by the commands {other.name!r} and {command.name!r}"
                )
            mapped[name] = command
    return mapped


class Commands:
    def __init__(
        self,
        *,
        plugins: Sequence[Command],
        general_options: Sequence[Option],
    ) -> None:
        super().__init__()
        self._command_map: Mapping[OptionName, Command] = _map_options(plugins)
        self._commands = plugins
        self._general_options = general_options

    def find(self, name: OptionName) -> Command | None:
        return self._command_map.get(name)

    def short_getopt_specs(self) -> str:
        options = "".join(HELP_OPTION.short_getopt_specs())
        for command in self._commands:
            options += "".join(command.short_getopt_specs())
        for option in self._general_options:
            options += "".join(option.short_getopt_specs())
        return options

    def long_getopt_specs(self) -> list[str]:
        options = HELP_OPTION.long_getopt_specs()
        for command in self._commands:
            options += command.long_getopt_specs()
        for option in self._general_options:
            options += option.long_getopt_specs()
        return options

    def help(self) -> str:
        return f"""WAYS TO CALL:
{self._short_help()}

OPTIONS:
{self._general_option_help()}

NOTES:
{self._long_help()}

"""

    def _short_help(self) -> str:
        texts = [command.short_help_text(" cmk %-36s") for command in self._commands]
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _long_help(self) -> str:
        texts = []
        for command in self._commands:
            text = command.long_help_text()
            if text:
                texts.append(text)
        return "\n\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _general_option_help(self) -> str:
        texts = [
            option.short_help_text(fmt="  %-21s")
            for option in [HELP_OPTION, *self._general_options]
        ]
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))
