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

import cmk.paths

import cmk_base.piggyback as piggyback

from .abstract import CheckMKAgentDataSource

class PiggyBackDataSource(CheckMKAgentDataSource):
    def id(self):
        return "piggyback"


    def describe(self):
        path = os.path.join(cmk.paths.tmp_dir, "piggyback", self._hostname)
        return "Process piggyback data from %s" % path


    def _execute(self):
        return piggyback.get_piggyback_raw_data(self._hostname) \
               + piggyback.get_piggyback_raw_data(self._ipaddress)


    def _get_raw_data(self):
        """Returns the current raw data of this data source

        Special for piggyback: No caching of raw data
        """
        self._logger.verbose("[%s] Execute data source" % self.id())
        return self._execute(), False


    def _summary_result(self):
        """Return no summary information for the piggyback data"""
        return 0, "", []
