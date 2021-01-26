#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import socket
from typing import Any, cast, Dict, List, Optional, Tuple, Union

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.exceptions import MKIPAddressLookupError, MKTerminate, MKTimeout
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName

import cmk.base.config as config

IPLookupCacheId = Tuple[HostName, socket.AddressFamily]
NewIPLookupCache = Dict[IPLookupCacheId, str]
LegacyIPLookupCache = Dict[str, str]
UpdateDNSCacheResult = Tuple[int, List[HostName]]

_fake_dns: Optional[HostAddress] = None
_enforce_localhost = False


def fallback_ip_for(family: socket.AddressFamily) -> str:
    return {
        socket.AF_INET: "0.0.0.0",
        socket.AF_INET6: "::",
    }.get(family, "::")


def deserialize_cache_id(serialized: Tuple[HostName, int]) -> Tuple[HostName, socket.AddressFamily]:
    # 4 and 6 are legacy values.
    return serialized[0], {4: socket.AF_INET, 6: socket.AF_INET6}[serialized[1]]


def serialize_cache_id(cache_id: Tuple[HostName, socket.AddressFamily]) -> Tuple[HostName, int]:
    # 4, 6 for legacy.
    return cache_id[0], {socket.AF_INET: 4, socket.AF_INET6: 6}[cache_id[1]]


def enforce_fake_dns(address: HostAddress) -> None:
    global _fake_dns
    _fake_dns = address


def enforce_localhost() -> None:
    global _enforce_localhost
    _enforce_localhost = True


def lookup_ipv4_address(host_config: config.HostConfig) -> Optional[HostAddress]:
    return lookup_ip_address(host_config, family=socket.AddressFamily.AF_INET)


def lookup_ipv6_address(host_config: config.HostConfig) -> Optional[HostAddress]:
    return lookup_ip_address(host_config, family=socket.AddressFamily.AF_INET6)


def lookup_mgmt_board_ip_address(host_config: config.HostConfig) -> Optional[HostAddress]:
    try:
        return lookup_ip_address(
            host_config,
            family=host_config.default_address_family,
            for_mgmt_board=True,
        )
    except MKIPAddressLookupError:
        return None


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(
    host_config: config.HostConfig,
    *,
    family: socket.AddressFamily,
    for_mgmt_board: bool = False,
) -> Optional[HostAddress]:
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns

    if config.fake_dns:
        return config.fake_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    if config.simulation_mode or _enforce_localhost or (host_config.is_usewalk_host and
                                                        host_config.is_snmp_host):
        return fallback_ip_for(family)

    hostname = host_config.hostname

    # Now check, if IP address is hard coded by the user
    if for_mgmt_board:
        # TODO Cleanup:
        # host_config.management_address also looks up "hostname" in ipaddresses/ipv6addresses
        # dependent on host_config.is_ipv6_primary as above. Thus we get the "right" IP address
        # here.
        ipa = host_config.management_address
    elif family is socket.AddressFamily.AF_INET:
        ipa = config.ipaddresses.get(hostname)
    else:
        ipa = config.ipv6addresses.get(hostname)

    if ipa:
        return ipa

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if host_config.is_dyndns_host:
        return hostname

    return cached_dns_lookup(hostname, family=family, is_no_ip_host=host_config.is_no_ip_host)


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(
    hostname: HostName,
    *,
    family: socket.AddressFamily,
    is_no_ip_host: bool,
) -> Optional[str]:
    cache = _config_cache.get("cached_dns_lookup")

    cache_id = hostname, family

    # Address has already been resolved in prior call to this function?
    try:
        return cache[cache_id]
    except KeyError:
        pass

    ip_lookup_cache = _get_ip_lookup_cache()

    cached_ip = ip_lookup_cache.get(cache_id)
    if cached_ip and config.use_dns_cache:
        cache[cache_id] = cached_ip
        return cached_ip

    if is_no_ip_host:
        cache[cache_id] = None
        return None

    # Now do the actual DNS lookup
    try:
        ipa = socket.getaddrinfo(hostname, None, family)[0][4][0]

        # Update our cached address if that has changed or was missing
        if ipa != cached_ip:
            console.verbose("Updating %s DNS cache for %s: %s\n" % (family, hostname, ipa))
            ip_lookup_cache.update_cache(cache_id, ipa)

        cache[cache_id] = ipa  # Update in-memory-cache
        return ipa

    except (MKTerminate, MKTimeout):
        # We should be more specific with the exception handler below, then we
        # could drop this special handling here
        raise

    except Exception as e:
        # DNS failed. Use cached IP address if present, even if caching
        # is disabled.
        if cached_ip:
            cache[cache_id] = cached_ip
            return cached_ip
        cache[cache_id] = None
        raise MKIPAddressLookupError("Failed to lookup %s address of %s via DNS: %s" % (
            {
                socket.AF_INET: "IPv4",
                socket.AF_INET6: "IPv6"
            }[family],
            hostname,
            e,
        ))


class IPLookupCache:
    def __init__(self, cache: cmk.utils.caching.DictCache) -> None:
        super().__init__()
        self._cache = cache
        self.persist_on_update = True

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._cache)

    def __eq__(self, other: Any) -> bool:
        return other == self._cache

    def __getitem__(self, key: Any) -> Any:
        return self._cache[key]

    def __len__(self) -> int:
        return len(self._cache)

    def get(self, key: Any) -> Optional[Any]:
        return self._cache.get(key)

    def load_persisted(self) -> None:
        try:
            self._cache.update(_load_ip_lookup_cache(lock=False))
        except (MKTerminate, MKTimeout):
            # We should be more specific with the exception handler below, then we
            # could drop this special handling here
            raise

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            # TODO: Would be better to log it somewhere to make the failure transparent

    def update_cache(self, cache_id: IPLookupCacheId, ipa: str) -> None:
        """Updates the cache with a new / changed entry

        When self.persist_on_update update is disabled, this simply updates the in-memory
        cache without any persistence interaction. Otherwise:

        The cache that was previously loaded into this IPLookupCache with load_persisted()
        might be outdated compared to the current persisted lookup cache. Another process
        might have updated the cache in the meantime.

        The approach here is to load the currently persisted cache with a lock, then update
        the current IPLookupCache with it, add the given new / changed entry and then write
        out the resulting data structure.

        This could really be solved in a better way, but may be sufficient for the moment.

        The cache can only be cleaned up with the "Update DNS cache" option in WATO
        or the "cmk --update-dns-cache" call that both call update_dns_cache().
        """
        if not self.persist_on_update:
            self._cache[cache_id] = ipa
            return

        try:
            self._cache.update(_load_ip_lookup_cache(lock=True))
            self._cache[cache_id] = ipa
            self.save_persisted()
        finally:
            store.release_lock(_cache_path())

    def save_persisted(self) -> None:
        store.save_object_to_file(
            _cache_path(),
            {serialize_cache_id(k): v for k, v in self._cache.items()},
            pretty=False,
        )

    def clear(self) -> None:
        """Clear the persisted AND in memory cache"""
        try:
            os.unlink(_cache_path())
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        self._cache.clear()


def _get_ip_lookup_cache() -> IPLookupCache:
    """A file based fall-back DNS cache in case resolution fails"""
    if "ip_lookup" in _config_cache:
        # Return already created and initialized cache
        return IPLookupCache(_config_cache.get("ip_lookup"))

    cache = IPLookupCache(_config_cache.get("ip_lookup"))
    cache.load_persisted()
    return cache


def _load_ip_lookup_cache(lock: bool) -> NewIPLookupCache:
    return _convert_legacy_ip_lookup_cache(
        store.load_object_from_file(_cache_path(), default={}, lock=lock))


def _convert_legacy_ip_lookup_cache(
        cache: Union[LegacyIPLookupCache, NewIPLookupCache]) -> NewIPLookupCache:
    """be compatible to old caches which were created by Check_MK without IPv6 support"""
    if not cache:
        return {}

    # New version has (hostname, ip family) as key
    if isinstance(list(cache)[0], tuple):
        return {deserialize_cache_id(cast(IPLookupCacheId, k)): v for k, v in cache.items()}

    cache = cast(LegacyIPLookupCache, cache)

    new_cache: NewIPLookupCache = {}
    for key, val in cache.items():
        new_cache[(key, socket.AF_INET)] = val
    return new_cache


def _cache_path() -> str:
    return cmk.utils.paths.var_dir + "/ipaddresses.cache"


def update_dns_cache() -> UpdateDNSCacheResult:
    config_cache = config.get_config_cache()

    failed = []

    ip_lookup_cache = _get_ip_lookup_cache()
    ip_lookup_cache.persist_on_update = False

    console.verbose("Cleaning up existing DNS cache...\n")
    ip_lookup_cache.clear()

    console.verbose("Updating DNS cache...\n")
    for hostname, family in _get_dns_cache_lookup_hosts(config_cache):
        host_config = config_cache.get_host_config(hostname)
        console.verbose("%s (IPv%d)..." % (hostname, family))
        try:
            ip = lookup_ip_address(host_config, family=family)
            console.verbose("%s\n" % ip)

        except (MKTerminate, MKTimeout):
            # We should be more specific with the exception handler below, then we
            # could drop this special handling here
            raise

        except Exception as e:
            failed.append(hostname)
            console.verbose("lookup failed: %s\n" % e)
            if cmk.utils.debug.enabled():
                raise
            continue

    ip_lookup_cache.persist_on_update = True
    ip_lookup_cache.save_persisted()

    return len(ip_lookup_cache), failed


def _get_dns_cache_lookup_hosts(config_cache: config.ConfigCache) -> List[IPLookupCacheId]:
    hosts = []
    for hostname in config_cache.all_active_hosts():
        host_config = config_cache.get_host_config(hostname)

        if host_config.is_ipv4_host:
            hosts.append((hostname, socket.AF_INET))

        if host_config.is_ipv6_host:
            hosts.append((hostname, socket.AF_INET6))

    return hosts
