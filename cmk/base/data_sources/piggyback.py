#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import json
from types import TracebackType  # pylint: disable=unused-import
from typing import Tuple, Type, Optional, List, Set  # pylint: disable=unused-import

from cmk.utils.log import VERBOSE
from cmk.utils.paths import tmp_dir
from cmk.utils.piggyback import (  # pylint: disable=unused-import
    get_piggyback_raw_data, PiggybackRawDataInfo, PiggybackTimeSettings,
)

import cmk.base.config as config
from cmk.base.check_utils import (  # pylint: disable=unused-import
    RawAgentData, ServiceCheckResult)
from cmk.utils.type_defs import HostName, HostAddress  # pylint: disable=unused-import

from .abstract import CheckMKAgentDataSource


def _raw_data(hostname, time_settings):
    # type: (Optional[str], PiggybackTimeSettings) -> List[PiggybackRawDataInfo]
    return get_piggyback_raw_data(hostname if hostname else "", time_settings)


class PiggyBackDataFetcher(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, hostname, ipaddress, time_settings):
        super(PiggyBackDataFetcher, self).__init__()
        self._hostname = hostname  # type: HostName
        self._ipaddress = ipaddress  # type: Optional[HostAddress]
        self._time_settings = time_settings  # type: List[Tuple[Optional[str], std, int]]
        self._sources = []  # type: List[PiggybackRawDataInfo]

    def __enter__(self):
        # type: () -> PiggyBackDataFetcher
        for origin in (self._hostname, self._ipaddress):
            self._sources.extend(_raw_data(origin, self._time_settings))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        self._sources.clear()

    def data(self):
        # type: () -> RawAgentData
        raw_data = b""
        raw_data += self._get_main_section()
        raw_data += self._get_source_labels_section()
        return raw_data

    def summary(self):
        # type: () -> ServiceCheckResult
        states = [0]
        infotexts = set()
        for src in self._sources:
            states.append(src.reason_status)
            infotexts.add(src.reason)
        return max(states), ", ".join(infotexts), []

    def _get_main_section(self):
        # type: () -> RawAgentData
        raw_data = b""
        for src in self._sources:
            if src.successfully_processed:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += src.raw_data
        return raw_data

    def _get_source_labels_section(self):
        # type: () -> RawAgentData
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return b""

        labels = {"cmk/piggyback_source_%s" % src.source_hostname: "yes" for src in self._sources}
        return b'<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels).encode("utf-8")


class PiggyBackDataSource(CheckMKAgentDataSource):
    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(PiggyBackDataSource, self).__init__(hostname, ipaddress)
        self._summary = None  # type: Optional[ServiceCheckResult]
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
        with PiggyBackDataFetcher(self._hostname, self._ipaddress, self._time_settings) as fetcher:
            raw_data = fetcher.data()
            self._summary = fetcher.summary()
        return raw_data

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

        if 'piggyback' in self._host_config.tags and not self._summary:
            # Tag: 'Always use and expect piggback data'
            return 1, 'Missing data', []

        if not self._summary:
            return 0, "", []

        return self._summary
