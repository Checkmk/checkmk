#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import textwrap
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from cmk.utils.exceptions import MKBailOut, MKGeneralException
from cmk.utils.log import console
from cmk.utils.plugin_loader import load_plugins
from cmk.utils.type_defs import HostName

import cmk.base.config as config

OptionSpec = str
Argument = str
OptionName = str
OptionFunction = Callable
ModeFunction = Callable
ConvertFunction = Callable
Options = List[Tuple[OptionSpec, Argument]]
Arguments = List[str]


class Modes:
    def __init__(self) -> None:
        super().__init__()
        self._mode_map: Dict[OptionName, Mode] = {}
        self._modes: List[Mode] = []
        self._general_options: List[Option] = []

    def register(self, mode: "Mode") -> None:
        self._modes.append(mode)

        self._mode_map[mode.long_option] = mode
        if mode.has_short_option():
            if mode.short_option is None:
                raise TypeError()
            self._mode_map[mode.short_option] = mode

    def exists(self, opt: OptionName) -> bool:
        try:
            self._get(opt)
            return True
        except KeyError:
            return False

    def call(
        self, opt: str, arg: Optional[Argument], all_opts: Options, all_args: Arguments
    ) -> int:
        mode = self._get(opt)
        sub_options = mode.get_sub_options(all_opts)

        handler_args: List = []
        if mode.sub_options:
            handler_args.append(sub_options)

        if mode.argument and mode.argument_optional:
            handler_args.append(all_args)
        elif mode.argument:
            handler_args.append(arg)

        handler = mode.handler_function
        if handler is None:
            raise TypeError()

        return handler(*handler_args)

    def _get(self, opt: str) -> "Mode":
        opt_name = self._strip_dashes(opt)
        return self._mode_map[opt_name]

    def _strip_dashes(self, opt: str) -> str:
        if opt.startswith("--"):
            return opt[2:]
        if opt.startswith("-"):
            return opt[1:]
        raise NotImplementedError()

    def get(self, name: OptionName) -> "Mode":
        return self._mode_map[name]

    def short_getopt_specs(self) -> str:
        options = ""
        for mode in self._modes:
            options += "".join(mode.short_getopt_specs())
        for option in self._general_options:
            options += "".join(option.short_getopt_specs())
        return options

    def long_getopt_specs(self) -> List[str]:
        options: List[str] = []
        for mode in self._modes:
            options += mode.long_getopt_specs()
        for option in self._general_options:
            options += option.long_getopt_specs()
        return options

    def short_help(self) -> str:
        texts = []
        for mode in self._modes:
            text = mode.short_help_text(" cmk %-36s")
            if text:
                texts.append(text)
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def long_help(self) -> str:
        texts = []
        for mode in self._modes:
            text = mode.long_help_text()
            if text:
                texts.append(text)
        return "\n\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def non_config_options(self) -> List[str]:
        options: List[str] = []
        for mode in self._modes:
            if not mode.needs_config:
                options += mode.options()
        return options

    def non_checks_options(self) -> List[str]:
        options: List[str] = []
        for mode in self._modes:
            if not mode.needs_checks:
                options += mode.options()
        return options

    def parse_hostname_list(
        self, args: List[str], with_clusters: bool = True, with_foreign_hosts: bool = False
    ) -> List[HostName]:
        config_cache = config.get_config_cache()
        if with_foreign_hosts:
            valid_hosts = config_cache.all_configured_realhosts()
        else:
            valid_hosts = config_cache.all_active_realhosts()

        if with_clusters:
            valid_hosts = valid_hosts.union(config_cache.all_active_clusters())

        hostlist = []
        for arg in args:
            if arg[0] != "@" and arg in valid_hosts:
                hostlist.append(arg)
            else:
                if arg[0] == "@":
                    arg = arg[1:]
                tagspec = arg.split(",")

                num_found = 0
                for hostname in valid_hosts:
                    if config.hosttags_match_taglist(
                        config_cache.tag_list_of_host(hostname), tagspec
                    ):
                        hostlist.append(hostname)
                        num_found += 1
                if num_found == 0:
                    raise MKBailOut(
                        "Hostname or tag specification '%s' does " "not match any host." % arg
                    )
        return hostlist

    #
    # GENERAL OPTIONS
    #

    def register_general_option(self, option: "Option") -> None:
        self._general_options.append(option)

    def process_general_options(self, all_opts: Options) -> None:
        for o, a in all_opts:
            option = self._get_general_option(o)
            if not option:
                continue

            if option.handler_function is None:
                raise TypeError()

            if option.takes_argument():
                option.handler_function(a)
            else:
                option.handler_function()

    def general_option_help(self) -> str:
        texts = []
        for option in self._general_options:
            text = option.short_help_text(fmt="  %-21s")
            if text:
                texts.append("%s" % text)
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _get_general_option(self, opt: str) -> "Optional[Option]":
        opt_name = self._strip_dashes(opt)
        for option in self._general_options:
            if opt_name in [option.long_option, option.short_option]:
                return option
        return None


class Option:
    def __init__(
        self,
        long_option: str,
        short_help: str,
        short_option: Optional[str] = None,
        argument: bool = False,
        argument_descr: Optional[str] = None,
        argument_conv: Optional[ConvertFunction] = None,
        argument_optional: bool = False,
        count: bool = False,
        handler_function: Optional[OptionFunction] = None,
        *,
        deprecated_long_options: Optional[Set[str]] = None,
    ) -> None:
        super().__init__()
        self.long_option = long_option
        self.short_help = short_help
        self.short_option = short_option
        self._deprecated_long_options = deprecated_long_options or set()

        # An option can either
        # a) have an argument
        # b) have no argument and count it's occurance
        # c) have no argument (will always be True in sub_options)
        self.count = count
        self.argument = argument
        self.argument_descr = argument_descr
        self.argument_conv = argument_conv
        self.argument_optional = argument_optional
        self.handler_function = handler_function

    def name(self) -> str:
        return self.long_option

    def options(self) -> List[str]:
        options = []
        if self.short_option:
            options.append(f"-{self.short_option}")
        options.append(f"--{self.long_option}")
        options.extend(f"--{opt}" for opt in self._deprecated_long_options)
        return options

    def is_deprecated_option(self, opt_str: str) -> bool:
        return opt_str.lstrip("-") in self._deprecated_long_options

    def has_short_option(self) -> bool:
        return self.short_option is not None

    def takes_argument(self) -> bool:
        return self.argument

    def short_help_text(self, fmt: str) -> Optional[str]:
        if self.short_help is None:
            return None

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

    def short_getopt_specs(self) -> List[str]:
        if not self.has_short_option():
            return []

        spec = self.short_option
        if spec is None:
            raise TypeError()
        if self.argument and not self.argument_optional:
            spec += ":"
        return [spec]

    def long_getopt_specs(self) -> List[str]:
        specs = [self.long_option]
        specs.extend(self._deprecated_long_options)
        if self.argument and not self.argument_optional:
            return [f"{spec}=" for spec in specs]
        return specs


class Mode(Option):
    def __init__(
        self,
        long_option: OptionName,
        handler_function: ModeFunction,
        short_help: str,
        short_option: Optional[OptionName] = None,
        argument: bool = False,
        argument_descr: Optional[str] = None,
        argument_conv: Optional[ConvertFunction] = None,
        argument_optional: bool = False,
        long_help: Optional[List[str]] = None,
        needs_config: bool = True,
        needs_checks: bool = True,
        sub_options: Optional[List[Option]] = None,
    ) -> None:
        super().__init__(
            long_option,
            short_help,
            short_option,
            argument,
            argument_descr,
            argument_conv,
            argument_optional,
            handler_function=handler_function,
        )
        self.long_help = long_help
        self.needs_config = needs_config
        self.needs_checks = needs_checks
        self.sub_options = sub_options or []

    def short_getopt_specs(self) -> List[str]:
        specs = super().short_getopt_specs()
        for option in self.sub_options:
            specs += option.short_getopt_specs()
        return specs

    def long_getopt_specs(self) -> List[str]:
        specs = super().long_getopt_specs()
        for option in self.sub_options:
            specs += option.long_getopt_specs()
        return specs

    # expected format is like this
    #  -i, --inventory does a HW/SW-Inventory for all, one or several
    #  hosts. If you add the option -f, --force then persisted sections
    #  will be used even if they are outdated.
    def long_help_text(self) -> Optional[str]:
        if not self.long_help and not self.sub_options:
            return None

        text: List[str] = []

        option_text = "  "
        if self.short_option:
            option_text += "-%s, " % self.short_option
        option_text += "--%s " % self.long_option

        if not self.long_help:
            text.append(option_text)
        else:
            for index, paragraph in enumerate(self.long_help):
                if index == 0:
                    initial_indent = option_text
                else:
                    initial_indent = "    "

                wrapper = textwrap.TextWrapper(
                    initial_indent=initial_indent,
                    subsequent_indent="    ",
                    width=80,
                )
                text.append(wrapper.fill(paragraph))

        if self.sub_options:
            sub_texts = []
            for option in self.sub_options:
                short_help_text = option.short_help_text(fmt="    %-24s")
                if short_help_text is not None:
                    sub_texts.append(short_help_text)
            text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

        return "\n\n".join(text)

    def get_sub_options(
        self, all_opts: Options
    ) -> Optional[Dict[OptionName, Union[Argument, int, bool]]]:
        if not self.sub_options:
            return None

        options: Dict[OptionName, Union[Argument, int, bool]] = {}

        for o, a in all_opts:
            for option in self.sub_options:
                if o not in option.options():
                    continue

                if option.is_deprecated_option(o):
                    console.warning("%r is deprecated in favour of option %r", o, option.name())

                if a and not option.takes_argument():
                    raise MKGeneralException("No argument to %s expected." % o)

                val: Union[Argument, bool] = a
                if not option.takes_argument():
                    if option.count:
                        value = options.setdefault(option.name(), 0)
                        if not isinstance(value, int):
                            raise TypeError()
                        options[option.name()] = value + 1
                        continue
                    val = True
                else:
                    if option.argument_conv:
                        try:
                            val = option.argument_conv(a)
                        except ValueError:
                            raise MKGeneralException("%s: Invalid argument" % o)

                options[option.name()] = val

        return options


keepalive_option = Option(
    long_option="keepalive",
    short_help="Execute in keepalive mode (CEE only)",
)

#
# Initialize the modes object and load all available modes
#

modes = Modes()

load_plugins(__file__, __package__)
