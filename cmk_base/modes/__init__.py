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

import glob
import os
import sys
import textwrap
import getopt

from cmk.exceptions import MKBailOut

__all__ = [ os.path.basename(f)[:-3]
            for f in glob.glob(os.path.dirname(__file__) + "/*.py")
            if os.path.basename(f) != "__init__.py" ]


class Modes(object):
    _modes    = {}
    _by_short = {}
    _by_long  = {}

    def register(self, mode):
        self._modes[mode.long_option] = mode
        self._by_long[mode.long_option] = mode

        if mode.has_short_option():
            self._modes[mode.short_option] = mode
            self._by_short[mode.short_option] = mode


    def exists(self, opt):
        try:
            self._get(opt)
            return True
        except KeyError:
            return False


    def call(self, opt, arg, all_opts, all_args):
        mode = self._get(opt)
        sub_options = mode.get_sub_options(all_opts)

        handler_args = []
        if sub_options:
            handler_args.append(sub_options)

        if mode.arguments == True:
            handler_args.append(all_args)
        elif mode.arguments:
            # TODO: Really needed?
            handler_args.append(arg)

        mode.handler_function(*handler_args)


    def _get(self, opt):
        if opt.startswith("--"):
            opt_name = opt[2:]
        elif opt.startswith("-"):
            opt_name = opt[1:]
        else:
            raise NotImplementedError()

        return self._modes[opt_name]


    def short_options(self):
        options = ""
        for opt_name, mode in self._by_short.items():
            options += opt_name
            if mode.arguments != False and mode.arguments != True:
                options += ":"
        return options


    def long_options(self):
        options = []
        for opt_name, mode in self._by_long.items():
            spec = opt_name
            if mode.arguments != False and mode.arguments != True:
                spec += "="
            options.append(spec)
            if mode.sub_options:
                options += mode.sub_options()
        return options


    def short_help(self):
        texts = []
        for mode in self._by_long.values():
            text = mode.short_help_text()
            if text:
                texts.append(" %s" % text)
        return "\n".join(sorted(texts, key=lambda x: x.lstrip(" -")))


    def long_help(self):
        texts = []
        for mode in self._by_long.values():
            text = mode.long_help_text()
            if text:
                texts.append(text)
        return "\n\n".join(sorted(texts, key=lambda x: x.lstrip(" -")))


    def non_config_options(self):
        options = []
        for mode in self._by_long.values():
            if not mode.needs_config:
                options += mode.options()
        return options


class Mode(object):
    def __init__(self, long_option, handler_function, short_help, short_option=None,
                 arguments=False, argument_descr=None, long_help=None,
                 needs_config=True, sub_options=None):
        self.long_option      = long_option
        self.short_option     = short_option
        self.handler_function = handler_function
        self.short_help       = short_help
        self.long_help        = long_help
        self.arguments        = arguments
        self.argument_descr   = argument_descr
        self.needs_config     = needs_config
        self.sub_option_specs = sub_options


    def options(self):
        options = []
        if self.short_option:
            options.append("-%s" % self.short_option)
        options.append("--%s" % self.long_option)
        return options


    def sub_options(self):
        options = []
        for option in self.sub_option_specs or []:
            if option[1]:
                options.append("%s=" % option[0])
            else:
                options.append("%s" % option[0])
        return options


    def has_short_option(self):
        return self.short_option != None


    # expected format is like this
    # cmk -h, --help                       print this help
    # TODO: Handle self.arguments
    def short_help_text(self):
        if self.short_help is None:
            return

        line = "cmk "
        line += " %s" % (", ".join(self.options()))

        if self.arguments:
            if self.argument_descr:
                line += " %s" % self.argument_descr
            else:
                line += " ..."

        return "%-37s%s" % (line, self.short_help)


    # expected format is like this
    #  -i, --inventory does a HW/SW-Inventory for all, one or several
    #  hosts. If you add the option -f, --force then persisted sections
    #  will be used even if they are outdated.
    def long_help_text(self):
        if not self.long_help and not self.sub_option_specs:
            return

        text = []
        for index, paragraph in enumerate(self.long_help or []):
            if index == 0:
                initial_indent = "  "
                if self.short_option:
                    initial_indent += "-%s, " % self.short_option
                initial_indent += "--%s " % self.long_option
            else:
                initial_indent = "    "

            wrapper = textwrap.TextWrapper(
                initial_indent=initial_indent,
                subsequent_indent="    ",
                width=78,
            )
            text.append(wrapper.fill(paragraph))

        if self.sub_option_specs:
            sub_text = "    Additional options:\n\n"
            for opt_name, argument_descr, _unused_conv, short_help in self.sub_option_specs:
                opt_descr = "--%s" % opt_name
                if argument_descr:
                    opt_descr += " %s" % argument_descr

                sub_text += "    %-12s %s" % (opt_descr, short_help)

            text.append(sub_text)

        return "\n\n".join(text)


    def get_sub_options(self, all_opts):
        if not self.sub_option_specs:
            return

        options = {}

        for o, a in all_opts:
            for opt_name, argument_descr, convert_func, _unused_2 in self.sub_option_specs:
                if o != "--%s" % opt_name:
                    continue

                if a and not argument_descr:
                    raise MKGeneralException("No argument to %s expected." % o)

                if convert_func:
                    try:
                        a = convert_func(a)
                    except ValueError:
                        raise MKGeneralException("%s: Invalid argument" % o)

                options[o.lstrip("-")] = a

        return options

#
# Initialize the modes object and load all available modes
#

modes = Modes()

from . import *
