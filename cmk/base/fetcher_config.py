#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: Check_MK Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path
from typing import Any, Optional, Dict

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.type_defs import HostName

import cmk.base.config as config
import cmk.base.core_config as core_config


class FetcherConfig:
    def __init__(self):
        # ! NOTE: This value will be checked by uint-test. Please synchronize with Microcore
        # grep for FetcherConfig.serial
        self.serial = 13  # TODO: Needs to be changed (increased?) on every create_config call

    def get_active_fetcher_config(self, hostname: HostName) -> Dict[str, Any]:
        """ Returns computed fetcher config """

        # TODO: Compute fetcher config for this host using other configuration data:
        # - including list of needed fetchers
        # - including the config of each fetcher
        # - dict format is in _get_predefined_fetcher_config
        # TODO: Handle all fetcher types: tests/unit/cmk/fetchers/test_fetchers.py

        return FetcherConfig._get_predefined_fetcher_config(hostname=hostname)

    @staticmethod
    def get_ip_address(hostname: HostName) -> Optional[str]:
        host_config = config.get_config_cache().get_host_config(hostname)

        if host_config.is_ipv4_host:
            return core_config.ip_address_of(host_config, 4)

        return core_config.ip_address_of(host_config, 6)

    @staticmethod
    def _get_predefined_fetcher_config(hostname: HostName) -> Dict[str, Any]:
        """ Example of correctly generated fetcher config. Used as temporary stub and reference"""

        ipaddress = FetcherConfig.get_ip_address(hostname)

        return {
            "fetchers": [
                {
                    "fetcher_type": "snmp",
                    "fetcher_params": {
                        # TODO: Use host check table to compute the OIDs needed by the services
                        "oid_infos": {
                            # "pim": [SNMPTree(base=".1.1.1", oids=["1.2", "3.4"]).to_json()],
                            # "pam": [SNMPTree(base=".1.2.3", oids=["4.5", "6.7", "8.9"]).to_json()],
                            # "pum": [
                            #    SNMPTree(base=".2.2.2", oids=["2.2"]).to_json(),
                            #    SNMPTree(base=".3.3.3", oids=["2.2"]).to_json(),
                            # ],
                        },
                        # TODO: Investigate which flags to use here
                        "use_snmpwalk_cache": False,
                        "snmp_config": config.HostConfig.make_snmp_config(
                            hostname=hostname,
                            address="" if ipaddress is None else ipaddress)._asdict(),
                    }
                },
                {
                    "fetcher_type": "program",
                    "fetcher_params": {
                        "cmdline": "/bin/true",
                        "stdin": None,
                        "is_cmc": False,
                    }
                },
            ]
        }

    # TODO: integration test is mandatory
    def write(self, hostname: HostName):
        """  Creates json files(one per active host) in fetcher-config directory """

        self.base_path.mkdir(parents=True, exist_ok=True)

        with self.config_file_path(hostname=hostname).open("w") as f:
            json.dump(obj=self.get_active_fetcher_config(hostname=hostname), fp=f)

    @property
    def base_path(self) -> Path:
        return Path(cmk.utils.paths.core_fetcher_config_dir, str(self.serial))

    def config_file_path(self, hostname: HostName) -> Path:
        return self.base_path / f"{hostname}.json"
