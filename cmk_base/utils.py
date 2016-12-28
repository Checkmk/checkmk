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

import os
import signal
import time

from cmk.exceptions import MKGeneralException, MKTerminate

# TODO: Try to find a better place for them.

import sys
import itertools


def make_utf8(x):
    if type(x) == unicode:
        return x.encode('utf-8')
    else:
        return x


# Aggegates several monitoring states to the worst state
def worst_service_state(*states):
    if 2 in states:
        return 2
    else:
        return max(states)


# Quote string for use as arguments on the shell
def quote_shell_string(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


# Works with Check_MK version (without tailing .cee and/or .demo)
def is_daily_build_version(v):
    return len(v) == 10 or '-' in v


# Works with Check_MK version (without tailing .cee and/or .demo)
def branch_of_daily_build(v):
    if len(v) == 10:
        return "master"
    else:
        return v.split('-')[0]


# Parses versions of Check_MK and converts them into comparable integers.
# This does not handle daily build numbers, only official release numbers.
# 1.2.4p1   -> 01020450001
# 1.2.4     -> 01020450000
# 1.2.4b1   -> 01020420100
# 1.2.3i1p1 -> 01020310101
# 1.2.3i1   -> 01020310100
# TODO: Copied to werks.py - find location for common code.
def parse_check_mk_version(v):
    def extract_number(s):
        number = ''
        for i, c in enumerate(s):
            try:
                int(c)
                number += c
            except ValueError:
                s = s[i:]
                return number and int(number) or 0, s
        return number and int(number) or 0, ''

    parts = v.split('.')
    while len(parts) < 3:
        parts.append("0")

    major, minor, rest = parts
    sub, rest = extract_number(rest)

    if not rest:
        val = 50000
    elif rest[0] == 'p':
        num, rest = extract_number(rest[1:])
        val = 50000 + num
    elif rest[0] == 'i':
        num, rest = extract_number(rest[1:])
        val = 10000 + num*100

        if rest and rest[0] == 'p':
            num, rest = extract_number(rest[1:])
            val += num
    elif rest[0] == 'b':
        num, rest = extract_number(rest[1:])
        val = 20000 + num*100

    return int('%02d%02d%02d%05d' % (int(major), int(minor), sub, val))


def total_size(o, handlers=None):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    if handlers == None:
        handlers = {}

    dict_handler = lambda d: itertools.chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = sys.getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen: # do not double count the same object
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
    except Exception, e:
        raise MKGeneralException("Cannot determine age of cache file %s: %s" \
                                 % (path, e))


# Reset some global variable to their original value. This
# is needed in keepalive mode.
# We could in fact do some positive caching in keepalive
# mode - e.g. the counters of the hosts could be saved in memory.
def cleanup_globals():
    import cmk_base.checks
    cmk_base.checks.set_hostname("unknown")
    import cmk_base.item_state
    cmk_base.item_state.cleanup_item_states()
    import cmk_base.core
    cmk_base.core.cleanup_inactive_timeperiods()
    import cmk_base.snmp
    cmk_base.snmp.cleanup_host_caches()
    import cmk_base.agent_data
    cmk_base.agent_data.cleanup_host_caches()


def has_feature(name):
    try:
        __import__("cmk_base.%s" % name)
        return True
    except ImportError:
        return False

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
