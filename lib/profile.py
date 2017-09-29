#!/usr/bin/python
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

"""A helper module to implement profiling functionalitiy. The main part
is to provide a contextmanager that can be added to existing code with
minimal changes."""

import cProfile
import contextlib
import os

import cmk.log


class Profile(object):
    def __init__(self, enabled=True, profile_file=None, *args, **kwargs):
        self._enabled = enabled
        self._profile_file = profile_file
        self._args = args
        self._kwargs = kwargs
        self._profile = None


    def __enter__(self):
        if self._enabled:
            cmk.log.logger.info("Recording profile")
            self._profile = cProfile.Profile(*self._args, **self._kwargs)
            self._profile.enable()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._enabled:
            return

        self._profile.disable()

        if not self._profile_file:
            self._profile.print_stats()
        else:
            self._profile.dump_stats(self._profile_file)
            cmk.log.logger.info("Created profile file: %s" % self._profile_file)

            file(self._profile_file + ".py", "w").write(
                "#!/usr/bin/env python\n"
                "import pstats\n"
                "stats = pstats.Stats(%r)\n"
                "stats.sort_stats('time').print_stats()\n" % self._profile_file)
            os.chmod(self._profile_file + ".py", 0o755)
            cmk.log.logger.info("Created profile dump script: %s.py" % self._profile_file)
