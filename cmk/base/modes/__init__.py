#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
import textwrap
import getopt
from typing import Union, Tuple, Callable, Optional, Dict, List  # pylint: disable=unused-import

from cmk.utils.plugin_loader import load_plugins
from cmk.utils.exceptions import MKBailOut, MKGeneralException
from cmk.utils.type_defs import HostName  # pylint: disable=unused-import

import cmk.base.config as config

OptionSpec = str
Argument = str
OptionName = str
OptionFunction = Callable
ModeFunction = Callable
ConvertFunction = Callable
Options = List[Tuple[OptionSpec, Argument]]
Arguments = List[str]


class Modes(object):
    def __init__(self):
        # type: () -> None
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        super(Modes, self).__init__()  # pylint: disable=bad-super-call
        self._mode_map = {}  # type: Dict[OptionName, Mode]
        self._modes = []  # type: List[Mode]
        self._general_options = []  # type: List[Option]

    def register(self, mode):
        # type: (Mode) -> None
        self._modes.append(mode)

        self._mode_map[mode.long_option] = mode
        if mode.has_short_option():
            if mode.short_option is None:
                raise TypeError()
            self._mode_map[mode.short_option] = mode

    def exists(self, opt):
        # type: (OptionName) -> bool
        try:
            self._get(opt)
            return True
        except KeyError:
            return False

    def call(self, opt, arg, all_opts, all_args):
        # type: (str, Optional[Argument], Options, Arguments) -> int
        mode = self._get(opt)
        sub_options = mode.get_sub_options(all_opts)

        handler_args = []  # type: List
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

    def _get(self, opt):
        # type: (str) -> Mode
        opt_name = self._strip_dashes(opt)
        return self._mode_map[opt_name]

    def _strip_dashes(self, opt):
        # type: (str) -> str
        if opt.startswith("--"):
            return opt[2:]
        elif opt.startswith("-"):
            return opt[1:]
        else:
            raise NotImplementedError()

    def get(self, name):
        # type: (OptionName) -> Mode
        return self._mode_map[name]

    def short_getopt_specs(self):
        # type: () -> str
        options = ""
        for mode in self._modes:
            options += "".join(mode.short_getopt_specs())
        for option in self._general_options:
            options += "".join(option.short_getopt_specs())
        return options

    def long_getopt_specs(self):
        # type: () -> List[str]
        options = []  # type: List[str]
        for mode in self._modes:
            options += mode.long_getopt_specs()
        for option in self._general_options:
            options += option.long_getopt_specs()
        return options

    def short_help(self):
        # type: () -> str
        texts = []
        for mode in self._modes:
            text = mode.short_help_text(" cmk %-36s")
            if text:
                texts.append(text)
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def long_help(self):
        # type: () -> str
        texts = []
        for mode in self._modes:
            text = mode.long_help_text()
            if text:
                texts.append(text)
        return "\n\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def non_config_options(self):
        # type: () -> List[str]
        options = []  # type: List[str]
        for mode in self._modes:
            if not mode.needs_config:
                options += mode.options()
        return options

    def non_checks_options(self):
        # type: () -> List[str]
        options = []  # type: List[str]
        for mode in self._modes:
            if not mode.needs_checks:
                options += mode.options()
        return options

    def parse_hostname_list(self, args, with_clusters=True, with_foreign_hosts=False):
        # type: (List[str], bool, bool) -> List[HostName]
        config_cache = config.get_config_cache()
        if with_foreign_hosts:
            valid_hosts = config_cache.all_configured_realhosts()
        else:
            valid_hosts = config_cache.all_active_realhosts()

        if with_clusters:
            valid_hosts = valid_hosts.union(config_cache.all_active_clusters())

        hostlist = []
        for arg in args:
            if arg[0] != '@' and arg in valid_hosts:
                hostlist.append(arg)
            else:
                if arg[0] == '@':
                    arg = arg[1:]
                tagspec = arg.split(',')

                num_found = 0
                for hostname in valid_hosts:
                    if config.hosttags_match_taglist(config_cache.tag_list_of_host(hostname),
                                                     tagspec):
                        hostlist.append(hostname)
                        num_found += 1
                if num_found == 0:
                    raise MKBailOut("Hostname or tag specification '%s' does "
                                    "not match any host." % arg)
        return hostlist

    #
    # GENERAL OPTIONS
    #

    def register_general_option(self, option):
        # type: (Option) -> None
        self._general_options.append(option)

    def process_general_options(self, all_opts):
        # type: (Options) -> None
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

    def general_option_help(self):
        # type: () -> str
        texts = []
        for option in self._general_options:
            text = option.short_help_text(fmt="  %-21s")
            if text:
                texts.append("%s" % text)
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -").lower()))

    def _get_general_option(self, opt):
        # type: (str) -> Optional[Option]
        opt_name = self._strip_dashes(opt)
        for option in self._general_options:
            if opt_name == option.long_option or opt_name == option.short_option:
                return option
        return None


class Option(object):
    def __init__(self,
                 long_option,
                 short_help,
                 short_option=None,
                 argument=False,
                 argument_descr=None,
                 argument_conv=None,
                 argument_optional=False,
                 count=False,
                 handler_function=None):
        # type: (str, str, str, bool, str, ConvertFunction, bool, bool, OptionFunction) -> None
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        super(Option, self).__init__()  # pylint: disable=bad-super-call
        self.long_option = long_option
        self.short_help = short_help
        self.short_option = short_option

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

    def name(self):
        # type: () -> str
        return self.long_option

    def options(self):
        # type: () -> List[str]
        options = []
        if self.short_option:
            options.append("-%s" % self.short_option)
        options.append("--%s" % self.long_option)
        return options

    def has_short_option(self):
        # type: () -> bool
        return self.short_option is not None

    def takes_argument(self):
        # type: () -> bool
        return self.argument

    def short_help_text(self, fmt):
        # type: (str) -> Optional[str]
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

    def short_getopt_specs(self):
        # type: () -> List[str]
        if not self.has_short_option():
            return []

        spec = self.short_option
        if spec is None:
            raise TypeError()
        if self.argument and not self.argument_optional:
            spec += ":"
        return [spec]

    def long_getopt_specs(self):
        # type: () -> List[str]
        spec = self.long_option
        if self.argument and not self.argument_optional:
            spec += "="
        return [spec]


class Mode(Option):
    def __init__(self,
                 long_option,
                 handler_function,
                 short_help,
                 short_option=None,
                 argument=False,
                 argument_descr=None,
                 argument_conv=None,
                 argument_optional=False,
                 long_help=None,
                 needs_config=True,
                 needs_checks=True,
                 sub_options=None):
        # type: (OptionName, ModeFunction, str, Optional[OptionName], bool, Optional[str], ConvertFunction, bool, Optional[List[str]], bool, bool, Optional[List[Option]]) -> None
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        # pylint: disable=bad-super-call
        super(Mode, self).__init__(long_option,
                                   short_help,
                                   short_option,
                                   argument,
                                   argument_descr,
                                   argument_conv,
                                   argument_optional,
                                   handler_function=handler_function)
        self.long_help = long_help
        self.needs_config = needs_config
        self.needs_checks = needs_checks
        self.sub_options = sub_options or []

    def short_getopt_specs(self):
        # type: () -> List[str]
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        specs = super(Mode, self).short_getopt_specs()  # pylint: disable=bad-super-call
        for option in self.sub_options:
            specs += option.short_getopt_specs()
        return specs

    def long_getopt_specs(self):
        # type: () -> List[str]
        # TODO: This disable is needed because of a pylint bug. Remove one day.
        specs = super(Mode, self).long_getopt_specs()  # pylint: disable=bad-super-call
        for option in self.sub_options:
            specs += option.long_getopt_specs()
        return specs

    # expected format is like this
    #  -i, --inventory does a HW/SW-Inventory for all, one or several
    #  hosts. If you add the option -f, --force then persisted sections
    #  will be used even if they are outdated.
    def long_help_text(self):
        # type: () -> Optional[str]
        if not self.long_help and not self.sub_options:
            return None

        text = []  # type: List[str]

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
                short_help_text = option.short_help_text(fmt="    %-21s")
                if short_help_text is not None:
                    sub_texts.append(short_help_text)
            text.append("    Additional options:\n\n%s" % "\n".join(sub_texts))

        return "\n\n".join(text)

    def get_sub_options(self, all_opts):
        # type: (Options) -> Optional[Dict[OptionName, Union[Argument, int, bool]]]
        if not self.sub_options:
            return None

        options = {}  # type: Dict[OptionName, Union[Argument, int, bool]]

        for o, a in all_opts:
            for option in self.sub_options:
                if o not in option.options():
                    continue

                if a and not option.takes_argument():
                    raise MKGeneralException("No argument to %s expected." % o)

                val = a  # type: Union[Argument, bool]
                if not option.takes_argument():
                    if option.count:
                        value = options.setdefault(option.name(), 0)
                        if not isinstance(value, int):
                            raise TypeError()
                        options[option.name()] = value + 1
                        continue
                    else:
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
