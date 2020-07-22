#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, cast, Dict, Final, Optional, Tuple

from cmk.utils.log import VERBOSE
from cmk.utils.paths import tmp_dir
from cmk.utils.piggyback import get_piggyback_raw_data
from cmk.utils.type_defs import HostAddress, HostName, RawAgentData, ServiceCheckResult, SourceType

from cmk.fetchers import PiggyBackDataFetcher

import cmk.base.config as config
from cmk.base.config import SelectedRawSections
from cmk.base.exceptions import MKAgentError

from ._abstract import ABCConfigurator
from .agent import AgentDataSource


class PiggyBackConfigurator(ABCConfigurator):
    def __init__(
        self,
        hostname: HostName,
        ipaddress: Optional[HostAddress],
    ) -> None:
        super().__init__(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            description=PiggyBackConfigurator._make_description(hostname),
            id_="piggyback",
            cpu_tracking_id="agent",
        )
        self.time_settings: Final = (config.get_config_cache().get_piggybacked_hosts_time_settings(
            piggybacked_hostname=hostname))

    def configure_fetcher(self) -> Dict[str, Any]:
        return {
            "hostname": self.hostname,
            "address": self.ipaddress,
            "time_settings": self.time_settings,
        }

    @staticmethod
    def _make_description(hostname: HostName):
        return "Process piggyback data from %s" % (Path(tmp_dir) / "piggyback" / hostname)


class PiggyBackDataSource(AgentDataSource):
    def __init__(
        self,
        *,
        configurator: PiggyBackConfigurator,
        main_data_source: bool = False,
    ) -> None:
        super(PiggyBackDataSource, self).__init__(
            configurator=configurator,
            main_data_source=main_data_source,
        )
        self._summary: Optional[ServiceCheckResult] = None

    def describe(self) -> str:
        return self.configurator.description

    def _execute(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> RawAgentData:
        self._summary = self._summarize()
        with PiggyBackDataFetcher.from_json(self.configurator.configure_fetcher()) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _summarize(self) -> ServiceCheckResult:
        states = [0]
        infotexts = set()
        # TODO(ml): Get rid of cast-the code is doubled with the fetcher
        #           so that this could actually go the the configurator.
        configurator = cast(PiggyBackConfigurator, self.configurator)
        for origin in (self.configurator.hostname, self.configurator.ipaddress):
            for src in get_piggyback_raw_data(
                    origin if origin else "",
                    configurator.time_settings,
            ):
                states.append(src.reason_status)
                infotexts.add(src.reason)
        return max(states), ", ".join(infotexts), []

    def _get_raw_data(
        self,
        *,
        selected_raw_sections: Optional[SelectedRawSections],
    ) -> Tuple[RawAgentData, bool]:
        """Returns the current raw data of this data source

        Special for piggyback: No caching of raw data
        """
        self._logger.log(VERBOSE, "Execute data source")
        return self._execute(selected_raw_sections=selected_raw_sections), False

    def _summary_result(self, for_checking: bool) -> ServiceCheckResult:
        """Returns useful information about the data source execution

        Return only summary information in case there is piggyback data"""

        if not for_checking:
            # Check_MK Discovery: Do not display information about piggyback files
            # and source status file
            return 0, '', []

        if 'piggyback' in self.configurator.host_config.tags and not self._summary:
            # Tag: 'Always use and expect piggback data'
            return 1, 'Missing data', []

        if not self._summary:
            return 0, "", []

        return self._summary
