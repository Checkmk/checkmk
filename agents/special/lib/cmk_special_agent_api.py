#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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


import sys, requests, getopt


"""Place for common code shared among different Check_MK special agents"""


class AgentJSON(object):
    def __init__(self, key, title):
        self._key = key
        self._title = title


    def usage(self):
        sys.stderr.write("""
Check_MK %s Agent

USAGE: agent_%s --section_url [{section_name},{url}]

    Parameters:
        --section_url   Pair of section_name and url
                        Can be defined multiple times
        --debug         Output json data with pprint

""" % (self._title, self._key))


    def get_content(self):
        short_options = "h"
        long_options  = ["section_url=", "help", "newline_replacement=", "debug"]

        try:
            opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
        except getopt.GetoptError, err:
            sys.stderr.write("%s\n" % err)
            sys.exit(1)

        sections = []
        newline_replacement = "\\n"
        opt_debug = False

        for o,a in opts:
            if o in [ "--section_url" ]:
                sections.append(a.split(",", 1))
            elif o in [ "--newline_replacement" ]:
                newline_replacement = a
            elif o in [ "--debug" ]:
                opt_debug = True
            elif o in [ '-h', '--help' ]:
                self.usage()
                sys.exit(0)

        if not sections:
            self.usage()
            sys.exit(0)

        content = {}
        for section_name, url in sections:
            content.setdefault(section_name, [])
            content[section_name].append(requests.get(url).text.replace("\n", newline_replacement))

        if opt_debug:
            import pprint, json
            for line in content:
                try:
                    pprint.pprint(json.loads(line))
                except:
                    print line
        else:
            return content
