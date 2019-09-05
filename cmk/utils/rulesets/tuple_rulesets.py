#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

from typing import NamedTuple, Generator, Dict, Text, Pattern, Tuple, List  # pylint: disable=unused-import

import cmk.utils.debug
from cmk.utils.regex import regex
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

# Conveniance macros for legacy tuple based host and service rules
PHYSICAL_HOSTS = ['@physical']  # all hosts but not clusters
CLUSTER_HOSTS = ['@cluster']  # all cluster hosts
ALL_HOSTS = ['@all']  # physical and cluster hosts
ALL_SERVICES = [""]  # optical replacement"
NEGATE = '@negate'  # negation in boolean lists

# TODO: We could make some more optimizations to host/item list matching:
# - Is it worth to detect matches that are no regex matches?
# - We could remove .* from end of regexes
# - What's about compilation of the regexes?


def get_rule_options(entry):
    """Get the options from a rule.

    Pick out the option element of a rule. Currently the options "disabled"
    and "comments" are being honored."""
    if isinstance(entry[-1], dict):
        return entry[:-1], entry[-1]

    return entry, {}


def in_extraconf_hostlist(hostlist, hostname):
    """Whether or not the given host matches the hostlist.

    Entries in list are hostnames that must equal the hostname.
    Expressions beginning with ! are negated: if they match,
    the item is excluded from the list.

    Expressions beginning with ~ are treated as regular expression.
    Also the three special tags '@all', '@clusters', '@physical'
    are allowed.
    """

    # Migration help: print error if old format appears in config file
    # FIXME: When can this be removed?
    try:
        if hostlist[0] == "":
            raise MKGeneralException('Invalid empty entry [ "" ] in configuration')
    except IndexError:
        pass  # Empty list, no problem.

    for hostentry in hostlist:
        if hostentry == '':
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        negate = False
        use_regex = False
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            # TODO: Is not used anymore for a long time. Will be cleaned up
            # with 1.6 tuple ruleset cleanup
            #ic = is_cluster(hostname)
            #if hostentry == '@cluster' and ic:
            #    return True
            #elif hostentry == '@physical' and not ic:
            #    return True

        # Allow negation of hostentry with prefix '!'
        else:
            if hostentry[0] == '!':
                hostentry = hostentry[1:]
                negate = True

            # Allow regex with prefix '~'
            if hostentry[0] == '~':
                hostentry = hostentry[1:]
                use_regex = True

        try:
            if not use_regex and hostname == hostentry:
                return not negate
            # Handle Regex. Note: hostname == True -> generic unknown host
            elif use_regex and hostname != True:
                if regex(hostentry).match(hostname) is not None:
                    return not negate
        except MKGeneralException:
            if cmk.utils.debug.enabled():
                raise

    return False


def hosttags_match_taglist(hosttags, required_tags):
    """Check if a host fulfills the requirements of a tag list.

    The host must have all tags in the list, except
    for those negated with '!'. Those the host must *not* have!
    A trailing + means a prefix match."""
    for tag in required_tags:
        negate, tag = _parse_negated(tag)
        if tag and tag[-1] == '+':
            tag = tag[:-1]
            matches = False
            for t in hosttags:
                if t.startswith(tag):
                    matches = True
                    break

        else:
            matches = tag in hosttags

        if matches == negate:
            return False

    return True


def convert_pattern_list(patterns):
    # type: (List[Text]) -> Optional[Pattern[Text]]
    """Compiles a list of service match patterns to a single regex

    Reducing the number of individual regex matches improves the performance dramatically.
    This function assumes either all or no pattern is negated (like WATO creates the rules).
    """
    if not patterns:
        return None

    pattern_parts = []

    for pattern in patterns:
        negate, pattern = _parse_negated(pattern)
        # Skip ALL_SERVICES from end of negated lists
        if negate:
            if pattern == ALL_SERVICES[0]:
                continue
            pattern_parts.append("(?!%s)" % pattern)
        else:
            pattern_parts.append("(?:%s)" % pattern)

    return regex("(?:%s)" % "|".join(pattern_parts))


def _parse_negated(pattern):
    # Allow negation of pattern with prefix '!'
    try:
        negate = pattern[0] == '!'
        if negate:
            pattern = pattern[1:]
    except IndexError:
        negate = False

    return negate, pattern
