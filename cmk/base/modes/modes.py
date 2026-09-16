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
from dataclasses import dataclass
from typing import Final, override

from cmk.base.base_app import CheckmkBaseApp
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.discover_plugins import discover_plugins_from_modules
from cmk.utils.log import console

OptionSpec = str
Argument = str
OptionName = str
ConvertFunction = Callable[[str], object]
Options = list[tuple[OptionSpec, Argument]]
Arguments = Sequence[str]


type ModeHandler = Callable[[CheckmkBaseApp, Mapping[str, object], Sequence[str]], int]
"""The signature of every mode's handler: the application, the parsed sub-options (empty if
the mode has none) and the positional arguments (none, exactly one, or all remaining ones,
depending on the declaration); it returns the exit status."""


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
                console.warning(
                    tty.format_warning(f"{o!r} is deprecated in favour of option {option.name!r}")
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


@dataclass(frozen=True)
class Flag:
    handler: Callable[[], None]


@dataclass(frozen=True)
class WithArgument:
    descr: str
    handler: Callable[[Argument], None]


Action = Flag | WithArgument


def _action_descr(action: Action) -> str | None:
    match action:
        case WithArgument(descr=descr):
            return descr
        case Flag():
            return None


class GeneralOption(Option):
    def __init__(
        self,
        *,
        long_option: OptionName,
        action: Action,
        short_help: str,
        short_option: OptionName | None = None,
    ) -> None:
        descr = _action_descr(action)
        super().__init__(
            long_option=long_option,
            short_help=short_help,
            short_option=short_option,
            argument=descr is not None,
            argument_descr=descr,
        )
        self.action = action


class Mode(Option):
    def __init__(
        self,
        *,
        long_option: OptionName,
        handler_function: ModeHandler,
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


def discover_modes() -> Sequence[Mode]:
    discovery_result = discover_plugins_from_modules(
        plugin_prefixes={Mode: "mode_"},
        module_names_by_priority=[
            # TODO: We need to get rid of this hard-coded list
            "cmk.base.modes.check_mk",
            "cmk.base.diagnostics",
            "cmk.base.localize",
            "cmk.base.notify",
            "cmk.base.nonfree.alert_handling",
            "cmk.base.nonfree.dump_protobufs",
            "cmk.base.nonfree.cmc_helpers",
            "cmk.base.nonfree.convert_rrds",
            "cmk.base.nonfree.compress_history",
            "cmk.bakery.base.mode",  # non-free, optional
            "cmk.plugins.bakery.modes.cap",  # non-free, optional
        ],
        skip_wrong_types=True,
        raise_errors=True,
    )
    return tuple(discovery_result.plugins.values())


def write_stdout(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


_DEFAULT_PAGER: Final = "less"

_PAGER_PROMPT: Final = (
    "?ltline %lt?L/%L.:byte %bB?s/%s..?e (END):?pB %pB\\%.. (press h for help or q to quit)"
)

_LESS_OPTIONS: Final = f"--no-init --prompt={_PAGER_PROMPT}$"


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


class Modes:
    def __init__(
        self,
        *,
        plugins: Sequence[Mode],
        general_options: Sequence[GeneralOption],
    ) -> None:
        super().__init__()
        modes = [*plugins, self.mode_help()]
        self._mode_map: Mapping[OptionName, Mode] = {
            **{m.long_option: m for m in modes},
            **{m.short_option: m for m in modes if m.short_option is not None},
        }
        self._modes = modes
        self._general_options = general_options

    def mode_help(self) -> Mode:
        # It's a little weird to implement the --help option like this,
        # but it is the easiest way to be consistent with how we use `getopt`.
        def _show_help(_app: object, _options: object, _args: object) -> int:
            write_paged(self.help())
            return 0

        return Mode(
            long_option="help",
            short_option="h",
            handler_function=_show_help,
            short_help="Print this help",
        )

    def find(self, name: OptionName) -> Mode | None:
        return self._mode_map.get(name)

    def short_getopt_specs(self) -> str:
        options = ""
        for mode in self._modes:
            options += "".join(mode.short_getopt_specs())
        for option in self._general_options:
            options += "".join(option.short_getopt_specs())
        return options

    def long_getopt_specs(self) -> list[str]:
        options: list[str] = []
        for mode in self._modes:
            options += mode.long_getopt_specs()
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
        texts = [mode.short_help_text(" cmk %-36s") for mode in self._modes]
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _long_help(self) -> str:
        texts = []
        for mode in self._modes:
            text = mode.long_help_text()
            if text:
                texts.append(text)
        return "\n\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    #
    # GENERAL OPTIONS
    #

    def process_general_options(self, all_opts: Options) -> None:
        for o, a in all_opts:
            if (option := self._get_general_option(o)) is None:
                continue

            match option.action:
                case Flag(handler=handler):
                    handler()
                case WithArgument(handler=handler):
                    handler(a)

    def _general_option_help(self) -> str:
        texts = [option.short_help_text(fmt="  %-21s") for option in self._general_options]
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _get_general_option(self, opt: str) -> GeneralOption | None:
        for option in self._general_options:
            if opt.lstrip("-") in [option.long_option, option.short_option]:
                return option
        return None
