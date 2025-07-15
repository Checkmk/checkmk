#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SNMP caching"""

from pathlib import Path

import cmk.ccc.cleanup
from cmk.ccc import store
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.snmplib import OID, SNMPDecodedString

# TODO: Replace this by generic caching
_g_single_oid_hostname: HostName | None = None
_g_single_oid_ipaddress: HostAddress | None = None
_g_single_oid_cache: dict[OID, SNMPDecodedString | None] | None = None


def initialize_single_oid_cache(
    host_name: HostName, ipaddress: HostAddress | None, from_disk: bool = False, *, cache_dir: Path
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
            _g_single_oid_cache = _load_single_oid_cache(host_name, ipaddress, cache_dir=cache_dir)
        else:
            _g_single_oid_cache = {}


def write_single_oid_cache(
    host_name: HostName, ipaddress: HostAddress | None, *, cache_dir: Path
) -> None:
    if not _g_single_oid_cache:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{host_name}.{ipaddress}"
    store.save_object_to_file(cache_path, _g_single_oid_cache, pprint_value=False)


def _load_single_oid_cache(
    host_name: HostName, ipaddress: HostAddress | None, cache_dir: Path
) -> dict[OID, SNMPDecodedString | None]:
    cache_path = cache_dir / f"{host_name}.{ipaddress}"
    return store.load_object_from_file(cache_path, default={})


def single_oid_cache() -> dict[OID, SNMPDecodedString | None]:
    assert _g_single_oid_cache is not None
    return _g_single_oid_cache


def cleanup_host_caches() -> None:
    _clear_other_hosts_oid_cache(None)


cmk.ccc.cleanup.register_cleanup(cleanup_host_caches)


def _clear_other_hosts_oid_cache(hostname: HostName | None) -> None:
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname
    if _g_single_oid_hostname != hostname:
        _g_single_oid_cache = None
        _g_single_oid_hostname = hostname
        _g_single_oid_ipaddress = None
