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
import json

from cmk.utils.log import VERBOSE
from cmk.utils.paths import tmp_dir

from cmk_base.config import piggyback_max_cachefile_age
from cmk_base.piggyback import get_piggyback_raw_data

from .abstract import CheckMKAgentDataSource


def _raw_data(hostname):
    return get_piggyback_raw_data(hostname, piggyback_max_cachefile_age)


class PiggyBackDataSource(CheckMKAgentDataSource):
    def __init__(self, hostname, ipaddress):
        super(PiggyBackDataSource, self).__init__(hostname, ipaddress)
        self._processed_file_reasons = set()

    def id(self):
        return "piggyback"

    def describe(self):
        path = os.path.join(tmp_dir, "piggyback", self._hostname)
        return "Process piggyback data from %s" % path

    def _execute(self):
        raw_data_from_sources = _raw_data(self._hostname) + _raw_data(self._ipaddress)

        raw_data = ""
        for source_raw_data in raw_data_from_sources:
            self._processed_file_reasons.add(source_raw_data.reason)
            if source_raw_data.successfully_processed:
                raw_data += source_raw_data.raw_data

        return raw_data + self._get_source_labels_section(
            [source_raw_data.source_hostname for source_raw_data in raw_data_from_sources])

    def _get_source_labels_section(self, source_hostnames):
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not source_hostnames:
            return ""

        labels = {"cmk/piggyback_source_%s" % name: "yes" for name in source_hostnames}
        return '<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels)

    def _get_raw_data(self):
        """Returns the current raw data of this data source

        Special for piggyback: No caching of raw data
        """
        self._logger.log(VERBOSE, "Execute data source")
        return self._execute(), False

    def _summary_result(self, for_checking):
        """Returns useful information about the data source execution

        Return only summary information in case there is piggyback data"""

        return 0, ", ".join(self._processed_file_reasons), []
