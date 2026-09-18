#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


import itertools
import pickle
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast, Final

from cmk.ccc.hostaddress import HostName, Hosts


def load_packed_config(config_path: Path) -> Mapping[str, object]:
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Returns the merged raw config dict; callers must invoke
    `perform_post_config_loading_actions` to build a `LoadingResult`.
    Compared to `load()`, the validations performed there don't need to be
    performed for the check helpers.

    See Also:
        cmk.base.core.nagios._dump_precompiled_hostcheck()

    """
    return {
        # We need to add the variables we filtered out here, because currently
        # We have to construct the full `LoadedConfig` (even if we don't need
        # it). This can go once we can serialize a dedicated datastructure.
        **PackedConfigGenerator.SKIPPED_CONFIG_VARIABLE_NAMES,
        **PackedConfigStore.from_serial(config_path).read(),
    }


def make_packed_config_writer(
    config: Mapping[str, object],
    hosts_config: Hosts,
    is_online: Callable[[HostName], bool],
    is_active: Callable[[HostName], bool],
) -> Callable[[Path], None]:

    def write(config_path: Path) -> None:
        """Create and store a precompiled configuration for Checkmk helper processes"""
        PackedConfigStore.from_serial(config_path).write(
            PackedConfigGenerator(
                hosts_config,
                config,
                is_online=is_online,
                is_active=is_active,
            ).generate()
        )

    return write


class PackedConfigGenerator:
    """The precompiled host checks and the CMC Check_MK helpers use a
    "precompiled" part of the Check_MK configuration during runtime.

    a) They must not use the live config from etc/check_mk during
       startup. They are only allowed to load the config activated by
       the user.

    b) They must not load the whole Check_MK config. Because they only
       need the options needed for checking
    """

    # These variables are part of the Checkmk configuration, but are not needed
    # by the Checkmk keepalive mode, so exclude them from the packed config
    SKIPPED_CONFIG_VARIABLE_NAMES = {
        "define_contactgroups": {},
        "define_hostgroups": {},
        "define_servicegroups": {},
        "service_contactgroups": [],
        "host_contactgroups": [],
        "service_groups": [],
        "host_groups": [],
        "contacts": {},
        "timeperiods": {},
        "extra_nagios_conf": "",
    }

    def __init__(
        self,
        hosts_config: Hosts,
        loaded_config: Mapping[str, object],
        is_online: Callable[[HostName], bool],
        is_active: Callable[[HostName], bool],
    ) -> None:
        self._hosts_config = hosts_config
        self._loaded_config = loaded_config
        self._is_online = is_online
        self._is_active = is_active

    def generate(self) -> Mapping[str, object]:
        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts = frozenset(
            hn
            for hn in itertools.chain(self._hosts_config.hosts, self._hosts_config.clusters)
            if self._is_active(hn) and self._is_online(hn)
        )

        def filter_all_hosts(all_hosts_orig: list[HostName]) -> list[HostName]:
            all_hosts_red = []
            for host_entry in all_hosts_orig:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(
            clusters_orig: dict[HostName, list[HostName]],
        ) -> dict[HostName, list[HostName]]:
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters_orig.items():
                clustername = HostName(cluster_entry.split("|", 1)[0])
                # Include offline cluster HOSTS.
                # Otherwise, services clustered to those hosts will wrongly be checked by the NODES.
                if clustername in self._hosts_config.clusters and self._is_active(clustername):
                    # But exclude offline cluster NODES.
                    # Otherwise, the check on the cluster HOST will fail.
                    clusters_red[cluster_entry] = [
                        node for node in cluster_nodes if node in active_hosts
                    ]
            return clusters_red

        def filter_hostname_in_dict(
            values: dict[HostName, dict[str, str]],
        ) -> dict[HostName, dict[str, str]]:
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        def filter_extra_service_conf(
            values: dict[str, list[dict[str, str]]],
        ) -> dict[str, list[dict[str, str]]]:
            return {
                "check_interval": values.get("check_interval", []),
                "_ec_sl": values.get("_ec_sl", []),
            }

        filter_var_functions: dict[str, Callable[[Any], Any]] = {
            "all_hosts": filter_all_hosts,
            "clusters": filter_clusters,
            "host_attributes": filter_hostname_in_dict,
            "ipaddresses": filter_hostname_in_dict,
            "ipv6addresses": filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags": filter_hostname_in_dict,  # unknown key, might be typo or legacy option
            "host_tags": filter_hostname_in_dict,
            "host_paths": filter_hostname_in_dict,
            "extra_service_conf": filter_extra_service_conf,
        }

        #
        # Add modified Checkmk base settings
        #
        return {
            k: filter_var_functions.get(k, lambda x: x)(v)
            for k, v in self._loaded_config.items()
            if k not in self.SKIPPED_CONFIG_VARIABLE_NAMES
        }


class PackedConfigStore:
    """Caring about persistence of the packed configuration"""

    def __init__(self, path: Path) -> None:
        self.path: Final = path

    @classmethod
    def from_serial(cls, config_path: Path) -> PackedConfigStore:
        return cls(cls.make_packed_config_store_path(config_path))

    @classmethod
    def make_packed_config_store_path(cls, config_path: Path) -> Path:
        return config_path / "precompiled_check_config.mk"

    def write(self, helper_config: Mapping[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.compiled")
        with tmp_path.open("wb") as compiled_file:
            pickle.dump(helper_config, compiled_file)
        tmp_path.rename(self.path)

    def read(self) -> Mapping[str, object]:
        with self.path.open("rb") as f:
            content = pickle.load(f)  # nosec B301 # BNS:c3c5e9
        return cast(Mapping[str, object], content)
