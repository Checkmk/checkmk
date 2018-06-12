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

from cmk.paths import tmp_dir

from cmk_base.config import piggyback_max_cachefile_age
from cmk_base.piggyback import get_piggyback_raw_data

from .abstract import CheckMKAgentDataSource


def _raw_data(name):
    return get_piggyback_raw_data(piggyback_max_cachefile_age, name)


class PiggyBackDataSource(CheckMKAgentDataSource):
    def id(self):
        return "piggyback"


    def describe(self):
        path = os.path.join(tmp_dir, "piggyback", self._hostname)
        return "Process piggyback data from %s" % path


    def _execute(self):
        return _raw_data(self._hostname) + _raw_data(self._ipaddress)

    def _get_raw_data(self):
        """Returns the current raw data of this data source

        Special for piggyback: No caching of raw data
        """
        self._logger.verbose("Execute data source")
        return self._execute(), False


    def _summary_result(self):
        """Return no summary information for the piggyback data"""
        return 0, "", []
