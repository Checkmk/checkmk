#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Dict, List, Optional, Tuple

from cmk.utils.log import VERBOSE
from cmk.utils.paths import tmp_dir
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData, ServiceCheckResult

from cmk.base.api import PluginName
from cmk.base.api.agent_based.section_types import AgentSectionPlugin
import cmk.base.config as config
from cmk.base.exceptions import MKAgentError

from cmk.fetchers import PiggyBackDataFetcher

from .abstract import CheckMKAgentDataSource


class PiggyBackDataSource(CheckMKAgentDataSource):
    def __init__(
            self,
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            selected_raw_sections=None,  # type: Optional[Dict[PluginName, config.SectionPlugin]]
    ):
        # type: (...) -> None
        super(PiggyBackDataSource, self).__init__(
            hostname,
            ipaddress,
            None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, AgentSectionPlugin)},
        )
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
            self._summary = fetcher.summary()
            return fetcher.data()
        raise MKAgentError("Failed to read data")

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
