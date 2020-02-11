#!/usr/bin/env python3
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

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import cmk.base.console as console

_profile = None
_profile_path = Path("profile.out")


def enable():
    # type: () -> None
    global _profile
    import cProfile  # pylint: disable=import-outside-toplevel
    _profile = cProfile.Profile()
    _profile.enable()
    console.verbose("Enabled profiling.\n")


def enabled():
    # type: () -> bool
    return _profile is not None


def output_profile():
    # type: () -> None
    if not _profile:
        return

    _profile.dump_stats(str(_profile_path))
    show_profile = _profile_path.with_name("show_profile.py")

    # TODO Change shebang as soon as we migrate to Python 3
    with show_profile.open("w") as f:
        f.write("""#!/usr/bin/env python
import sys
import pstats
try:
    profile_file = sys.argv[1]
except IndexError:
    profile_file = %s
stats = pstats.Stats(profile_file)
stats.sort_stats('time').print_stats()""" % _profile_path)

    show_profile.chmod(0o755)
    console.output("Profile '%s' written. Please run %s.\n" % (_profile_path, show_profile),
                   stream=sys.stderr)
