#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SNMP caching"""

import os
from typing import Dict, List, Optional

import cmk.utils.cleanup
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import HostAddress, HostName

from .type_defs import OID, SNMPDecodedString, SNMPHostConfig

# TODO: Replace this by generic caching
_g_single_oid_hostname: Optional[HostName] = None
_g_single_oid_ipaddress: Optional[HostAddress] = None
_g_single_oid_cache: Optional[Dict[OID, Optional[SNMPDecodedString]]] = None
# TODO: Move to StoredWalkSNMPBackend?
_g_walk_cache: Dict[str, List[str]] = {}


def initialize_single_oid_cache(snmp_config: SNMPHostConfig, from_disk: bool = False) -> None:
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname

    if (not (_g_single_oid_hostname == snmp_config.hostname and
             _g_single_oid_ipaddress == snmp_config.ipaddress) or _g_single_oid_cache is None):
        _g_single_oid_hostname = snmp_config.hostname
        _g_single_oid_ipaddress = snmp_config.ipaddress
        if from_disk:
            _g_single_oid_cache = _load_single_oid_cache(snmp_config)
        else:
            _g_single_oid_cache = {}


def write_single_oid_cache(snmp_config: SNMPHostConfig) -> None:
    if not _g_single_oid_cache:
        return

    cache_dir = cmk.utils.paths.snmp_scan_cache_dir
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_path = "%s/%s.%s" % (cache_dir, snmp_config.hostname, snmp_config.ipaddress)
    store.save_object_to_file(cache_path, _g_single_oid_cache, pretty=False)


def set_single_oid_cache(oid: OID, value: Optional[SNMPDecodedString]) -> None:
    assert _g_single_oid_cache is not None
    _g_single_oid_cache[oid] = value


def is_in_single_oid_cache(oid: OID) -> bool:
    assert _g_single_oid_cache is not None
    return oid in _g_single_oid_cache


def get_oid_from_single_oid_cache(oid: OID) -> Optional[SNMPDecodedString]:
    assert _g_single_oid_cache is not None
    return _g_single_oid_cache.get(oid)


def _load_single_oid_cache(snmp_config: SNMPHostConfig) -> Dict[OID, Optional[SNMPDecodedString]]:
    cache_path = "%s/%s.%s" % (cmk.utils.paths.snmp_scan_cache_dir, snmp_config.hostname,
                               snmp_config.ipaddress)
    return store.load_object_from_file(cache_path, default={})


def cleanup_host_caches() -> None:
    global _g_walk_cache
    _g_walk_cache = {}
    _clear_other_hosts_oid_cache(None)


cmk.utils.cleanup.register_cleanup(cleanup_host_caches)


def host_cache_contains(name: HostName) -> bool:
    return name in _g_walk_cache


def host_cache_get(name: HostName) -> List[str]:
    return _g_walk_cache[name]


def host_cache_set(name: HostName, contents: List[str]) -> None:
    _g_walk_cache[name] = contents


def _clear_other_hosts_oid_cache(hostname: Optional[str]) -> None:
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname
    if _g_single_oid_hostname != hostname:
        _g_single_oid_cache = None
        _g_single_oid_hostname = hostname
        _g_single_oid_ipaddress = None
