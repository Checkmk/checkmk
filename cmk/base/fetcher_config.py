#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Optional

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.type_defs import HostAddress, HostName

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.data_sources import fetcher_configuration


class FetcherConfig:
    def __init__(self):
        # ! NOTE: This value will be checked by uint-test. Please synchronize with Microcore
        # grep for FetcherConfig.serial
        self.serial = 13  # TODO: Needs to be changed (increased?) on every create_config call

    @property
    def base_path(self) -> Path:
        return Path(cmk.utils.paths.core_fetcher_config_dir, str(self.serial))

    @staticmethod
    def get_ip_address(hostname: HostName) -> Optional[HostAddress]:
        host_config = config.get_config_cache().get_host_config(hostname)

        if host_config.is_ipv4_host:
            return core_config.ip_address_of(host_config, 4)

        return core_config.ip_address_of(host_config, 6)

    def write(self, hostname: HostName):
        """  Creates json files(one per active host) in fetcher-config directory """
        ipaddress = self.get_ip_address(hostname)
        self.base_path.mkdir(parents=True, exist_ok=True)
        with self.config_file_path(hostname=hostname).open("w") as f:
            fetcher_configuration.dump(hostname, ipaddress, f)

    def config_file_path(self, hostname: HostName) -> Path:
        return self.base_path / f"{hostname}.json"
