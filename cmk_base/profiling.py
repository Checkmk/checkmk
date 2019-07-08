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

import os
import sys

import cmk_base.console as console

_profile = None
_profile_path = "profile.out"


def enable():
    global _profile
    import cProfile
    _profile = cProfile.Profile()
    _profile.enable()
    console.verbose("Enabled profiling.\n")


def enabled():
    return _profile is not None


def output_profile():
    if not _profile:
        return

    _profile.dump_stats(_profile_path)
    show_profile = os.path.join(os.path.dirname(_profile_path), "show_profile.py")
    with open(show_profile, "w") as f:
        f.write("#!/usr/bin/env python\n"
                "import sys\n"
                "import pstats\n"
                "try:\n"
                "    profile_file = sys.argv[1]\n"
                "except IndexError:\n"
                "    profile_file = %r\n"
                "stats = pstats.Stats(profile_file)\n"
                "stats.sort_stats('time').print_stats()\n" % _profile_path)
    os.chmod(show_profile, 0755)

    console.output("Profile '%s' written. Please run %s.\n" % (_profile_path, show_profile),
                   stream=sys.stderr)
