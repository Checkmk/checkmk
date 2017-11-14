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

class HostInfo(object):
    """A wrapper class for the host information read by the data sources"""

    def __init__(self, info=None, cache_info=None, piggybacked_lines=None):
        self.info = info if info is not None else {}
        self.cache_info = cache_info if cache_info is not None else {}
        self.piggybacked_lines = piggybacked_lines if piggybacked_lines is not None else {}


    # TODO: It should be supported that different sources produce equal sections.
    # this is handled for the self.info data by simply concatenating the lines
    # of the sections, but for the self.cache_info this is not done. Why?
    # TODO: checking.execute_check() is using the oldest cached_at and the largest interval.
    #       Would this be correct here?
    def update(self, host_info):
        """Update this host info object with the contents of another one"""
        for check_type, lines in host_info.info.items():
            self.info.setdefault(check_type, []).extend(lines)

        for hostname, lines in host_info.piggybacked_lines.items():
            self.piggybacked_lines.setdefault(hostname, []).extend(lines)

        if host_info.cache_info:
            self.cache_info.update(host_info.cache_info)


    def add_cached_section(self, section_name, section, persisted_from, persisted_until):
        self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
        self.info[section_name] = section
