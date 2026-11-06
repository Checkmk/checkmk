#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import textwrap
from collections.abc import Mapping, Sequence
from typing import Final, override

from cmk.cli.internal import CommandHandler

from .options import HELP_OPTION, Option, OptionName


class GetoptCommand(Option):
    def __init__(
        self,
        *,
        name: str,
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
        self._name: Final = name
        self.handler_function = handler_function
        self.long_help = long_help
        self.sub_options = sub_options

    @property
    @override
    def name(self) -> str:
        return self._name

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


def _map_options(commands: Sequence[GetoptCommand]) -> Mapping[OptionName, GetoptCommand]:
    """Map every spelling of every command to it, rejecting a collision.

    Two commands claiming the same option would otherwise shadow one another
    silently, and the one that loses simply could not be invoked.
    """
    reserved = {HELP_OPTION.long_option, HELP_OPTION.short_option}
    mapped: dict[OptionName, GetoptCommand] = {}
    for command in commands:
        for name in (command.long_option, command.short_option):
            if name is None:
                continue
            if name in reserved:
                raise ValueError(f"{name!r} is the help, not the command {command.name!r}")
            if (other := mapped.get(name)) is not None:
                raise ValueError(
                    f"{name!r} is claimed by the commands {other.name!r} and {command.name!r}"
                )
            mapped[name] = command
    return mapped


class Commands:
    def __init__(
        self,
        *,
        plugins: Sequence[GetoptCommand],
        general_options: Sequence[Option],
    ) -> None:
        super().__init__()
        self._command_map: Mapping[OptionName, GetoptCommand] = _map_options(plugins)
        self._commands = plugins
        self._general_options = general_options

    def find(self, name: OptionName) -> GetoptCommand | None:
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
