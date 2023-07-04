#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SNMP caching"""

import os

import cmk.utils.cleanup
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.hostaddress import HostAddress, HostName

from .type_defs import OID, SNMPDecodedString

# TODO: Replace this by generic caching
_g_single_oid_hostname: HostName | None = None
_g_single_oid_ipaddress: HostAddress | None = None
_g_single_oid_cache: dict[OID, SNMPDecodedString | None] | None = None


def initialize_single_oid_cache(
    host_name: HostName, ipaddress: HostAddress | None, from_disk: bool = False
) -> None:
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname

    if (
        _g_single_oid_hostname != host_name
        or _g_single_oid_ipaddress != ipaddress
        or _g_single_oid_cache is None
    ):
        _g_single_oid_hostname = host_name
        _g_single_oid_ipaddress = ipaddress
        if from_disk:
            _g_single_oid_cache = _load_single_oid_cache(host_name, ipaddress)
        else:
            _g_single_oid_cache = {}


def write_single_oid_cache(host_name: HostName, ipaddress: HostAddress | None) -> None:
    if not _g_single_oid_cache:
        return

    cache_dir = cmk.utils.paths.snmp_scan_cache_dir
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_path = f"{cache_dir}/{host_name}.{ipaddress}"
    store.save_object_to_file(cache_path, _g_single_oid_cache, pretty=False)


def _load_single_oid_cache(
    host_name: HostName, ipaddress: HostAddress | None
) -> dict[OID, SNMPDecodedString | None]:
    cache_path = f"{cmk.utils.paths.snmp_scan_cache_dir}/{host_name}.{ipaddress}"
    return store.load_object_from_file(cache_path, default={})


def single_oid_cache() -> dict[OID, SNMPDecodedString | None]:
    assert _g_single_oid_cache is not None
    return _g_single_oid_cache


def cleanup_host_caches() -> None:
    _clear_other_hosts_oid_cache(None)


cmk.utils.cleanup.register_cleanup(cleanup_host_caches)


def _clear_other_hosts_oid_cache(hostname: HostName | None) -> None:
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname
    if _g_single_oid_hostname != hostname:
        _g_single_oid_cache = None
        _g_single_oid_hostname = hostname
        _g_single_oid_ipaddress = None
