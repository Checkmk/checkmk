#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Optional, Protocol, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.exceptions import MKIPAddressLookupError, MKTerminate, MKTimeout
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, UpdateDNSCacheResult

IPLookupCacheId = Tuple[HostName, socket.AddressFamily]


_fake_dns: Optional[HostAddress] = None
_enforce_localhost = False


class _HostConfigLike(Protocol):
    """This is what we expect from a HostConfig in *this* module"""

    # Importing of the HostConfig class repeatedly lead to import cycles at various places.
    hostname: HostName
    is_ipv4_host: bool
    is_ipv6_host: bool
    is_no_ip_host: bool
    is_snmp_host: bool
    is_usewalk_host: bool

    @property
    def default_address_family(self) -> socket.AddressFamily:
        ...

    @property
    def management_address(self) -> Optional[HostAddress]:
        ...

    @property
    def is_dyndns_host(self) -> bool:
        ...


def fallback_ip_for(family: socket.AddressFamily) -> HostAddress:
    return {
        socket.AF_INET: "0.0.0.0",
        socket.AF_INET6: "::",
    }.get(family, "::")


def enforce_fake_dns(address: HostAddress) -> None:
    global _fake_dns
    _fake_dns = address


def enforce_localhost() -> None:
    global _enforce_localhost
    _enforce_localhost = True


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(
    *,
    host_name: HostName,
    family: socket.AddressFamily,
    configured_ip_address: Optional[HostAddress],
    simulation_mode: bool,
    is_snmp_usewalk_host: bool,
    override_dns: Optional[HostAddress],
    is_dyndns_host: bool,
    is_no_ip_host: bool,
    force_file_cache_renewal: bool,
) -> Optional[HostAddress]:
    """This function *may* look up an IP address, or return a host name"""
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns

    if override_dns:
        return override_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    if simulation_mode or _enforce_localhost or is_snmp_usewalk_host:
        return "127.0.0.1" if family is socket.AF_INET else "::1"

    # check if IP address is hard coded by the user
    if configured_ip_address:
        return configured_ip_address

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if is_dyndns_host:
        return host_name

    return (
        None
        if is_no_ip_host
        else cached_dns_lookup(
            host_name,
            family=family,
            force_file_cache_renewal=force_file_cache_renewal,
        )
    )


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(
    hostname: HostName,
    *,
    family: socket.AddressFamily,
    force_file_cache_renewal: bool,
) -> Optional[HostAddress]:
    """Cached DNS lookup in *two* caching layers

    1) outer layer (this function):
       A *config cache* that caches all calls until the configuration is changed or runtime ends.
       Other than activating a changed configuration there is no way to remove cached results during
       runtime. Changes made by a differend process will not be noticed.
       This layer caches `None` for lookups that failed, after raising the corresponding exception
       *once*. Subsequent lookups for this hostname / family combination  will not raise an
       exception, until the configuration is changed.

    2) inner layer: see _file_cached_dns_lookup
    """
    cache = _config_cache.get("cached_dns_lookup")
    cache_id = hostname, family

    # Address has already been resolved in prior call to this function?
    try:
        return cache[cache_id]
    except KeyError:
        pass

    try:
        ip_address = _file_cached_dns_lookup(
            hostname,
            family,
            force_file_cache_renewal=force_file_cache_renewal,
        )
    except MKIPAddressLookupError:
        cache[cache_id] = None
        raise

    return cache.setdefault(cache_id, ip_address)


def _file_cached_dns_lookup(
    hostname: HostName,
    family: socket.AddressFamily,
    *,
    force_file_cache_renewal: bool,
) -> HostAddress:
    # TODO: is there any point in the IPLookupCache being cached in the
    # *config cache*? It seems to me it could well be kept during the entire
    # runtime, which means a) this could be a decorator and b) we could use
    # the same mechanism that the value store uses.
    """Resolve DNS using a file based cache

    This layer caches *successful* lookups of host name / IP address family combinations, and writes
    them to a file.

    Note that after the file is loaded initially, the data in the IPLookupCache is keept in sync
    with the file, and itself stored in a dict in the config cache.
    Before a new value is writte to file, the file is re-read, as another process might have changed
    it.
    """
    ip_lookup_cache = _get_ip_lookup_cache()
    cache_id = hostname, family

    cached_ip = ip_lookup_cache.get(cache_id)
    if cached_ip and not force_file_cache_renewal:
        return cached_ip

    ipa = _actual_dns_lookup(host_name=hostname, family=family, fallback=cached_ip)

    if ipa != cached_ip:
        family_str = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}[family]
        console.verbose(f"Updating {family_str} DNS cache for {hostname}: {ipa}\n")
        ip_lookup_cache[cache_id] = ipa

    return ipa


def _actual_dns_lookup(
    *,
    host_name: HostName,
    family: socket.AddressFamily,
    fallback: Optional[HostAddress] = None,
) -> HostAddress:
    try:
        return socket.getaddrinfo(host_name, None, family)[0][4][0]
    except (MKTerminate, MKTimeout):
        # We should be more specific with the exception handler below, then we
        # could drop this special handling here
        raise
    except Exception as e:
        if fallback:
            return fallback
        family_str = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}[family]
        raise MKIPAddressLookupError(
            f"Failed to lookup {family_str} address of {host_name} via DNS: {e}"
        )


class IPLookupCacheSerializer:
    def __init__(self) -> None:
        self._dim_serializer = store.DimSerializer()

    def serialize(self, data: Mapping[IPLookupCacheId, HostAddress]) -> bytes:
        return self._dim_serializer.serialize(
            {
                (str(hn), {socket.AF_INET: 4, socket.AF_INET6: 6}[f]): v
                for (hn, f), v in data.items()
            }
        )

    def deserialize(self, raw: bytes) -> Mapping[IPLookupCacheId, HostAddress]:
        loaded_object = self._dim_serializer.deserialize(raw)
        assert isinstance(loaded_object, dict)

        return {
            (HostName(k), socket.AF_INET)  # old pre IPv6 style
            if isinstance(k, str)
            else (HostName(k[0]), {4: socket.AF_INET, 6: socket.AF_INET6}[k[1]]): HostAddress(v)
            for k, v in loaded_object.items()
        }


class IPLookupCache:

    PATH = Path(cmk.utils.paths.var_dir, "ipaddresses.cache")

    def __init__(self, cache: MutableMapping[IPLookupCacheId, HostAddress]) -> None:
        self._cache = cache
        self._persist_on_update = True
        self._store = store.ObjectStore(self.PATH, serializer=IPLookupCacheSerializer())

    @contextmanager
    def persisting_disabled(self) -> Iterator[None]:
        old_persist_flag = self._persist_on_update
        self._persist_on_update = False
        try:
            yield
        finally:
            self._persist_on_update = old_persist_flag

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._cache)

    def __eq__(self, other: Any) -> bool:
        return other == self._cache

    def __getitem__(self, key: IPLookupCacheId) -> HostAddress:
        return self._cache[key]

    def __len__(self) -> int:
        return len(self._cache)

    def get(self, key: IPLookupCacheId) -> Optional[HostAddress]:
        return self._cache.get(key)

    def load_persisted(self) -> None:
        try:
            self._cache.update(self._store.read_obj(default={}))
        except (MKTerminate, MKTimeout):
            # We should be more specific with the exception handler below, then we
            # could drop this special handling here
            raise

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            # TODO: Would be better to log it somewhere to make the failure transparent

    def __setitem__(self, cache_id: IPLookupCacheId, ipa: HostAddress) -> None:
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
        if not self._persist_on_update:
            self._cache[cache_id] = ipa
            return

        with self._store.locked():
            self._cache.update(self._store.read_obj(default={}))
            self._cache[cache_id] = ipa
            self.save_persisted()

    def save_persisted(self) -> None:
        self._store.write_obj(self._cache)

    def clear(self) -> None:
        """Clear the persisted AND in memory cache"""
        self._cache.clear()
        self.save_persisted()


def _get_ip_lookup_cache() -> IPLookupCache:
    """A file based fall-back DNS cache in case resolution fails"""
    if "ip_lookup" in _config_cache:
        # Return already created and initialized cache
        return IPLookupCache(_config_cache.get("ip_lookup"))

    cache = IPLookupCache(_config_cache.get("ip_lookup"))
    cache.load_persisted()
    return cache


def update_dns_cache(
    *,
    host_configs: Iterable[_HostConfigLike],
    configured_ipv4_addresses: Mapping[HostName, HostAddress],
    configured_ipv6_addresses: Mapping[HostName, HostAddress],
    # Do these two even make sense? If either is set, this function
    # will just clear the cache.
    simulation_mode: bool,
    override_dns: Optional[HostAddress],
) -> UpdateDNSCacheResult:

    failed = []

    ip_lookup_cache = _get_ip_lookup_cache()

    with ip_lookup_cache.persisting_disabled():

        console.verbose("Cleaning up existing DNS cache...\n")
        ip_lookup_cache.clear()

        console.verbose("Updating DNS cache...\n")
        for host_config, family in _annotate_family(host_configs):
            console.verbose(f"{host_config.hostname} ({family})...")
            try:
                ip = lookup_ip_address(
                    host_name=host_config.hostname,
                    family=family,
                    configured_ip_address=(
                        configured_ipv4_addresses
                        if family is socket.AF_INET
                        else configured_ipv4_addresses
                    ).get(host_config.hostname),
                    simulation_mode=simulation_mode,
                    is_snmp_usewalk_host=host_config.is_usewalk_host and host_config.is_snmp_host,
                    override_dns=override_dns,
                    is_dyndns_host=host_config.is_dyndns_host,
                    is_no_ip_host=host_config.is_no_ip_host,
                    force_file_cache_renewal=True,  # it's cleared anyway
                )
                console.verbose(f"{ip}\n")

            except (MKTerminate, MKTimeout):
                # We should be more specific with the exception handler below, then we
                # could drop this special handling here
                raise
            except MKIPAddressLookupError as e:
                failed.append(host_config.hostname)
                console.verbose("lookup failed: %s\n" % e)
                continue
            except Exception as e:
                failed.append(host_config.hostname)
                console.verbose("lookup failed: %s\n" % e)
                if cmk.utils.debug.enabled():
                    raise
                continue

    ip_lookup_cache.save_persisted()

    return len(ip_lookup_cache), failed


def _annotate_family(
    host_configs: Iterable[_HostConfigLike],
) -> Iterable[Tuple[_HostConfigLike, socket.AddressFamily]]:
    for host_config in host_configs:

        if host_config.is_ipv4_host:
            yield host_config, socket.AF_INET

        if host_config.is_ipv6_host:
            yield host_config, socket.AF_INET6
