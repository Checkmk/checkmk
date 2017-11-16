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

import time

import cmk_base.console as console

class HostInfo(object):
    """A wrapper class for the host information read by the data sources

    It contains the following information:

        1. info:              A dictionary from "sectionname" to a list of rows
        2. piggybacked_lines: piggy-backed data for other hosts
        3. persisted_info:    Sections to be persisted for later usage
        4. cache_info:        Agent cache information
                              (dict section name -> (cached_at, cache_interval))
    """


    def __init__(self, info=None, cache_info=None, piggybacked_lines=None, persisted_info=None):
        self.info = info if info is not None else {}
        self.cache_info = cache_info if cache_info is not None else {}
        self.piggybacked_lines = piggybacked_lines if piggybacked_lines is not None else {}
        self.persisted_info = persisted_info if persisted_info is not None else {}


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

        if host_info.persisted_info:
            self.persisted_info.update(host_info.persisted_info)


    def _add_cached_section(self, section_name, section, persisted_from, persisted_until):
        self.cache_info[section_name] = (persisted_from, persisted_until - persisted_from)
        self.info[section_name] = section


    def update_with_persisted_info(self, persisted_info, use_outdated_sections):
        for section_name, entry in persisted_info.items():
            if len(entry) == 2:
                continue # Skip entries of "old" format

            persisted_from, persisted_until, section_info = entry

            # Don't overwrite sections that have been received from the source with this call
            if section_name not in self.info:
                console.vverbose("Using persisted section %r\n" % section_name)
                self._add_cached_section(section_name, section_info, persisted_from, persisted_until)
            else:
                console.vverbose("Skipping persisted section %r\n" % section_name)
