#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import json
from typing import Tuple, Optional, List, Set  # pylint: disable=unused-import

from cmk.utils.log import VERBOSE
from cmk.utils.paths import tmp_dir
from cmk.utils.piggyback import (  # pylint: disable=unused-import
    get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings,
)

import cmk.base.config as config
from cmk.base.check_utils import (  # pylint: disable=unused-import
    RawAgentData, ServiceCheckResult, ServiceState, ServiceDetails,
)
from cmk.utils.type_defs import HostName, HostAddress  # pylint: disable=unused-import

from .abstract import CheckMKAgentDataSource


def _raw_data(hostname, time_settings):
    # type: (HostName, PiggybackTimeSettings) -> List[PiggybackRawDataInfo]
    return get_piggyback_raw_data(hostname, time_settings)


class PiggyBackDataSource(CheckMKAgentDataSource):
    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(PiggyBackDataSource, self).__init__(hostname, ipaddress)
        self._processed_file_reasons = set()  # type: Set[Tuple[ServiceState, ServiceDetails]]
        self._time_settings = config.get_config_cache().get_piggybacked_hosts_time_settings(
            piggybacked_hostname=self._hostname)

    def id(self):
        # type: () -> str
        return "piggyback"

    def describe(self):
        # type: () -> str
        path = os.path.join(tmp_dir, "piggyback", self._hostname)
        return "Process piggyback data from %s" % path

    def _execute(self):
        # type: () -> RawAgentData
        raw_data_from_sources = _raw_data(self._hostname, self._time_settings)

        if self._ipaddress is not None:
            raw_data_from_sources += _raw_data(self._ipaddress, self._time_settings)

        raw_data = b""
        for source_raw_data in raw_data_from_sources:
            self._processed_file_reasons.add(
                (source_raw_data.reason_status, source_raw_data.reason))
            if source_raw_data.successfully_processed:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - raw_data_from_sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += source_raw_data.raw_data

        return raw_data + self._get_source_labels_section(
            [source_raw_data.source_hostname for source_raw_data in raw_data_from_sources])

    def _get_source_labels_section(self, source_hostnames):
        # type: (List[HostName]) -> RawAgentData
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not source_hostnames:
            return b""

        labels = {"cmk/piggyback_source_%s" % name: "yes" for name in source_hostnames}
        return b'<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels).encode("utf-8")

    def _get_raw_data(self):
        # type: () -> Tuple[RawAgentData, bool]
        """Returns the current raw data of this data source

        Special for piggyback: No caching of raw data
        """
        self._logger.log(VERBOSE, "Execute data source")
        return self._execute(), False

    def _summary_result(self, for_checking):
        # type: (bool) -> ServiceCheckResult
        """Returns useful information about the data source execution

        Return only summary information in case there is piggyback data"""

        if not for_checking:
            # Check_MK Discovery: Do not display information about piggyback files
            # and source status file
            return 0, '', []

        if 'piggyback' in self._host_config.tags and not self._processed_file_reasons:
            # Tag: 'Always use and expect piggback data'
            return 1, 'Missing data', []

        states = [0]
        infotexts = []
        for reason_status, reason in self._processed_file_reasons:
            states.append(reason_status)
            infotexts.append(reason)
        return max(states), ", ".join(infotexts), []
