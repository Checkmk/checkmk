#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import socket
from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.exceptions import MKIPAddressLookupError, MKTerminate, MKTimeout
from cmk.utils.log import console
from cmk.utils.type_defs import HostAddress, HostName, UpdateDNSCacheResult

from cmk.snmplib.type_defs import SNMPBackendEnum  # pylint: disable=cmk-module-layer-violation

IPLookupCacheId = tuple[HostName | HostAddress, socket.AddressFamily]


_fake_dns: HostAddress | None = None
_enforce_localhost = False


@enum.unique
class AddressFamily(enum.IntFlag):
    NO_IP = enum.auto()
    IPv4 = enum.auto()
    IPv6 = enum.auto()
    DUAL_STACK = IPv4 | IPv6

    @classmethod
    def from_socket(cls, /, af: socket.AddressFamily) -> AddressFamily:
        match af:
            case socket.AF_INET:
                return cls.IPv4
            case socket.AF_INET6:
                return cls.IPv6
            case _:
                raise ValueError(af)


class IPLookupConfig(NamedTuple):
    hostname: HostName
    address_family: AddressFamily
    is_snmp_host: bool
    snmp_backend: SNMPBackendEnum
    default_address_family: socket.AddressFamily
    management_address: HostAddress | None
    is_dyndns_host: bool


def fallback_ip_for(family: socket.AddressFamily | AddressFamily) -> HostAddress:
    if isinstance(family, socket.AddressFamily):
        family = AddressFamily.from_socket(family)
    match family:
        case AddressFamily.IPv4:
            return "0.0.0.0"
        case AddressFamily.IPv6:
            return "::"
        case _:
            # TODO(ml): [IPv6] This ignores `default_address_family()`
            # and falls back to IPv6, where IPv4 is the default almost
            # everywhere else.  Using "0.0.0.0" or "::" only makes sense
            # for a server anyway, so the users of this function are
            # most likely misconfigured.
            return "::"


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
    host_name: HostName | HostAddress,
    family: AddressFamily | socket.AddressFamily,
    configured_ip_address: HostAddress | None,
    simulation_mode: bool,
    is_snmp_usewalk_host: bool,
    override_dns: HostAddress | None,
    is_dyndns_host: bool,
    force_file_cache_renewal: bool,
) -> HostAddress | None:
    """This function *may* look up an IP address, or return a host name"""
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns

    if override_dns:
        return override_dns

    if isinstance(family, socket.AddressFamily):
        family = AddressFamily.from_socket(family)

    # Honor simulation mode und usewalk hosts. Never contact the network.
    if simulation_mode or _enforce_localhost or is_snmp_usewalk_host:
        return "::1" if AddressFamily.IPv6 in family else "127.0.0.1"

    # check if IP address is hard coded by the user
    if configured_ip_address:
        return configured_ip_address

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if is_dyndns_host:
        return host_name

    if family is AddressFamily.NO_IP:
        return None

    return cached_dns_lookup(
        host_name,
        # NO_IP handled in guard.
        # TODO(ml): [IPv6] Default to IPv4 for DUAL_STACK.  Why doesn't this
        # obey `default_address_family()` or handle both addresses in that case?
        family=socket.AF_INET if AddressFamily.IPv4 in family else socket.AF_INET6,
        force_file_cache_renewal=force_file_cache_renewal,
    )


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(
    hostname: HostName | HostAddress,
    *,
    family: socket.AddressFamily,
    force_file_cache_renewal: bool,
) -> HostAddress | None:
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
    cache: dict[
        tuple[HostName | HostAddress, socket.AddressFamily], HostAddress | None
    ] = _config_cache.get("cached_dns_lookup")
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
    hostname: HostName | HostAddress,
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
    host_name: HostName | HostAddress,
    family: socket.AddressFamily,
    fallback: HostAddress | None = None,
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
        return f"{type(self).__name__}({self._cache!r})"

    def __eq__(self, other: Any) -> bool:
        return other == self._cache

    def __getitem__(self, key: IPLookupCacheId) -> HostAddress:
        return self._cache[key]

    def __len__(self) -> int:
        return len(self._cache)

    def get(self, key: IPLookupCacheId) -> HostAddress | None:
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
    ip_lookup_configs: Iterable[IPLookupConfig],
    configured_ipv4_addresses: Mapping[HostName | HostAddress, HostAddress],
    configured_ipv6_addresses: Mapping[HostName | HostAddress, HostAddress],
    # Do these two even make sense? If either is set, this function
    # will just clear the cache.
    simulation_mode: bool,
    override_dns: HostAddress | None,
) -> UpdateDNSCacheResult:
    failed = []

    ip_lookup_cache = _get_ip_lookup_cache()

    with ip_lookup_cache.persisting_disabled():
        console.verbose("Cleaning up existing DNS cache...\n")
        ip_lookup_cache.clear()

        console.verbose("Updating DNS cache...\n")
        # `_annotate_family()` handles DUAL_STACK and NO_IP
        for host_name, host_config, family in _annotate_family(ip_lookup_configs):
            console.verbose(f"{host_name} ({family})...")
            try:
                ip = lookup_ip_address(
                    host_name=host_name,
                    family=family,
                    configured_ip_address=(
                        configured_ipv4_addresses
                        if family is socket.AF_INET
                        else configured_ipv6_addresses
                    ).get(host_name),
                    simulation_mode=simulation_mode,
                    is_snmp_usewalk_host=(
                        host_config.snmp_backend is SNMPBackendEnum.STORED_WALK
                        and host_config.is_snmp_host
                    ),
                    override_dns=override_dns,
                    is_dyndns_host=host_config.is_dyndns_host,
                    force_file_cache_renewal=True,  # it's cleared anyway
                )
                console.verbose(f"{ip}\n")

            except (MKTerminate, MKTimeout):
                # We should be more specific with the exception handler below, then we
                # could drop this special handling here
                raise
            except MKIPAddressLookupError as e:
                failed.append(host_name)
                console.verbose("lookup failed: %s\n" % e)
                continue
            except Exception as e:
                failed.append(host_name)
                console.verbose("lookup failed: %s\n" % e)
                if cmk.utils.debug.enabled():
                    raise
                continue

    ip_lookup_cache.save_persisted()

    return len(ip_lookup_cache), failed


def _annotate_family(
    ip_lookup_configs: Iterable[IPLookupConfig],
) -> Iterable[tuple[HostName, IPLookupConfig, socket.AddressFamily]]:
    for host_config in ip_lookup_configs:
        if AddressFamily.IPv4 in host_config.address_family:
            yield host_config.hostname, host_config, socket.AF_INET
        if AddressFamily.IPv6 in host_config.address_family:
            yield host_config.hostname, host_config, socket.AF_INET6
