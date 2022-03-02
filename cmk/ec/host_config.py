#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from threading import Lock
from typing import Optional

from cmk.utils.type_defs import HostName, Timestamp

from .core_queries import HostInfo, query_hosts_infos, query_status_program_start

# .
#   .--Host config---------------------------------------------------------.
#   |          _   _           _                      __ _                 |
#   |         | | | | ___  ___| |_    ___ ___  _ __  / _(_) __ _           |
#   |         | |_| |/ _ \/ __| __|  / __/ _ \| '_ \| |_| |/ _` |          |
#   |         |  _  | (_) \__ \ |_  | (_| (_) | | | |  _| | (_| |          |
#   |         |_| |_|\___/|___/\__|  \___\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   | Manages the configuration of the hosts of the local monitoring core. |
#   | It fetches and caches the information during runtine of the EC.      |
#   '----------------------------------------------------------------------'


class HostConfig:
    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._lock = Lock()
        self._hosts_by_name: dict[HostName, HostInfo] = {}
        self._hosts_by_designation: dict[str, HostName] = {}
        self._cache_timestamp: Optional[Timestamp] = None

    def get_config_for_host(self, host_name: HostName) -> Optional[HostInfo]:
        with self._lock:
            return (
                self._hosts_by_name.get(host_name)
                if self._update_cache_after_core_restart()
                else None
            )

    def get_canonical_name(self, event_host_name: str) -> Optional[HostName]:
        with self._lock:
            return (
                self._hosts_by_designation.get(event_host_name.lower())
                if self._update_cache_after_core_restart()
                else None
            )

    def _update_cache_after_core_restart(self) -> bool:
        """Once the core reports a restart update the cache

        Returns:
            False in case the update failed, otherwise True.
        """
        try:
            timestamp = query_status_program_start()
            if self._cache_timestamp is None or self._cache_timestamp < timestamp:
                self._update_cache()
                self._cache_timestamp = timestamp
        except Exception:
            self._logger.exception("Failed to get host info from core. Try again later.")
            return False
        return True

    def _update_cache(self) -> None:
        self._logger.debug("Fetching host config from core")
        self._hosts_by_name.clear()
        self._hosts_by_designation.clear()
        for info in query_hosts_infos():
            self._hosts_by_name[info.name] = info
            # Note: It is important that we use exactly the same algorithm here as
            # in the core, see World::loadHosts and World::getHostByDesignation.
            if info.address:
                self._hosts_by_designation[info.address.lower()] = info.name
            if info.alias:
                self._hosts_by_designation[info.alias.lower()] = info.name
            self._hosts_by_designation[info.name.lower()] = info.name
        self._logger.debug("Got %d hosts from core" % len(self._hosts_by_name))
