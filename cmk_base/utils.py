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
"""This is an unsorted collection of functions which are needed in
Check_MK modules and/or cmk_base modules code."""

import itertools
import os
import signal
import sys
import time

from cmk.utils.exceptions import MKGeneralException, MKTerminate

# TODO: Try to find a better place for them.


# Aggegates several monitoring states to the worst state
def worst_service_state(*states):
    if 2 in states:
        return 2
    return max(states)


# Works with Check_MK version (without tailing .cee and/or .demo)
def is_daily_build_version(v):
    return len(v) == 10 or '-' in v


# Works with Check_MK version (without tailing .cee and/or .demo)
def branch_of_daily_build(v):
    if len(v) == 10:
        return "master"
    return v.split('-')[0]


def total_size(o, handlers=None):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    if handlers is None:
        handlers = {}

    dict_handler = lambda d: itertools.chain.from_iterable(d.items())
    all_handlers = {
        tuple: iter,
        list: iter,
        dict: dict_handler,
        set: iter,
        frozenset: iter,
    }
    all_handlers.update(handlers)  # user handlers take precedence
    seen = set()  # track which object id's have already been seen
    default_size = sys.getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = sys.getsizeof(o, default_size)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


def cachefile_age(path):
    try:
        return time.time() - os.stat(path)[8]
    except Exception as e:
        raise MKGeneralException("Cannot determine age of cache file %s: %s" \
                                 % (path, e))


#.
#   .--Ctrl-C--------------------------------------------------------------.
#   |                     ____ _        _        ____                      |
#   |                    / ___| |_ _ __| |      / ___|                     |
#   |                   | |   | __| '__| |_____| |                         |
#   |                   | |___| |_| |  | |_____| |___                      |
#   |                    \____|\__|_|  |_|      \____|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Handling of Ctrl-C                                                  |
#   '----------------------------------------------------------------------'


# register SIGINT handler for consistent CTRL+C handling
def _handle_keepalive_interrupt(signum, frame):
    raise MKTerminate()


def register_sigint_handler():
    signal.signal(signal.SIGINT, _handle_keepalive_interrupt)
