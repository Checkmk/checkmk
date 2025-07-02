#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import ipaddress
import socket
from collections.abc import (
    Callable,
    Container,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, assert_never, Final, Generic, Literal, Protocol, TypeVar

import cmk.ccc.debug
from cmk.ccc import store
from cmk.ccc.exceptions import MKIPAddressLookupError, MKTerminate, MKTimeout
from cmk.ccc.hostaddress import HostAddress, HostName

import cmk.utils.paths
from cmk.utils.caching import cache_manager
from cmk.utils.log import console

IPLookupCacheId = tuple[HostName | HostAddress, socket.AddressFamily]


_fake_dns: HostAddress | None = None
_enforce_localhost = False

_FALLBACK_V4 = HostAddress("0.0.0.0")
_FALLBACK_V6 = HostAddress("::")


# keep the protocols here for now,
# they could be duplcated to achieve better separation.
class IPLookup(Protocol):
    def __call__(
        self,
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress: ...


class IPLookupOptional(Protocol):
    def __call__(
        self,
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress | None: ...


_TErrHandler = TypeVar("_TErrHandler", bound=Callable[[HostName, Exception], None])


@enum.unique
class IPStackConfig(enum.IntFlag):
    NO_IP = enum.auto()
    IPv4 = enum.auto()
    IPv6 = enum.auto()
    DUAL_STACK = IPv4 | IPv6


@dataclass(frozen=True, kw_only=True)
class IPLookupConfig:
    ip_stack_config: Callable[[HostName], IPStackConfig]
    is_snmp_host: Callable[[HostName], bool]
    is_snmp_management: Callable[[HostName], bool]
    is_use_walk_host: Callable[[HostName], bool]
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ]
    management_address: Callable[
        [HostName, Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]],
        HostAddress | None,
    ]
    is_dyndns_host: Callable[[HostName], bool]
    ipv4_addresses: Mapping[HostName, HostAddress]
    ipv6_addresses: Mapping[HostName, HostAddress]
    simulation_mode: bool
    fake_dns: HostAddress | None
    use_dns_cache: bool


def make_lookup_mgmt_board_ip_address(
    ip_config: IPLookupConfig,
) -> IPLookupOptional:
    def lookup_mgmt_board_ip_address(
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress | None:
        mgmt_address: Final = ip_config.management_address(host_name, family)
        try:
            mgmt_ipa = (
                None
                if mgmt_address is None
                else HostAddress(str(ipaddress.ip_address(mgmt_address)))
            )
        except (ValueError, TypeError):
            mgmt_ipa = None

        try:
            return _lookup_ip_address(
                # host name is ignored, if mgmt_ipa is trueish.
                host_name=mgmt_address or host_name,
                family=family,
                configured_ip_address=mgmt_ipa,
                simulation_mode=ip_config.simulation_mode,
                is_snmp_usewalk_host=(
                    ip_config.is_use_walk_host(host_name)
                    and ip_config.is_snmp_management(host_name)
                ),
                override_dns=ip_config.fake_dns,
                is_dyndns_host=ip_config.is_dyndns_host(host_name),
                force_file_cache_renewal=not ip_config.use_dns_cache,
            )
        except MKIPAddressLookupError:
            return None

    return lookup_mgmt_board_ip_address


def make_lookup_ip_address(
    ip_config: IPLookupConfig,
) -> IPLookup:
    def _wrapped_lookup(
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress:
        return _lookup_ip_address(
            host_name=host_name,
            family=family,
            configured_ip_address=(
                ip_config.ipv4_addresses
                if family is socket.AddressFamily.AF_INET
                else ip_config.ipv6_addresses
            ).get(host_name),
            simulation_mode=ip_config.simulation_mode,
            is_snmp_usewalk_host=(
                ip_config.is_use_walk_host(host_name) and ip_config.is_snmp_host(host_name)
            ),
            override_dns=ip_config.fake_dns,
            is_dyndns_host=ip_config.is_dyndns_host(host_name),
            force_file_cache_renewal=not ip_config.use_dns_cache,
        )

    return _wrapped_lookup


class ConfiguredIPLookup(Generic[_TErrHandler]):
    def __init__(
        self,
        lookup: Callable[
            [HostName, Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]],
            HostAddress,
        ],
        *,
        allow_empty: Container[HostName],
        error_handler: _TErrHandler,
    ) -> None:
        self._lookup: Final = lookup
        self.error_handler: Final[_TErrHandler] = error_handler
        self._allow_empty: Final = allow_empty

    def __call__(
        self,
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress:
        try:
            return self._lookup(host_name, family)
        except Exception as e:
            if host_name in self._allow_empty:
                return HostAddress("")
            self.error_handler(host_name, e)

        return fallback_ip_for(family)


def fallback_ip_for(
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
) -> HostAddress:
    match family:
        case socket.AddressFamily.AF_INET:
            return _FALLBACK_V4
        case socket.AddressFamily.AF_INET6:
            return _FALLBACK_V6
        case other:
            assert_never(other)


def is_fallback_ip(ip: HostAddress | str) -> bool:
    return HostAddress(ip) in (_FALLBACK_V4, _FALLBACK_V6)


def _local_ip_for(
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
) -> HostAddress:
    match family:
        case socket.AddressFamily.AF_INET:
            return HostAddress("127.0.0.1")
        case socket.AddressFamily.AF_INET6:
            return HostAddress("::1")
        case other:
            assert_never(other)


def enforce_fake_dns(address: HostAddress) -> None:
    global _fake_dns
    _fake_dns = address


def enforce_localhost() -> None:
    global _enforce_localhost
    _enforce_localhost = True


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved.
def _lookup_ip_address(
    *,
    host_name: HostName | HostAddress,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    configured_ip_address: HostAddress | None,
    simulation_mode: bool,
    is_snmp_usewalk_host: bool,
    override_dns: HostAddress | None,
    is_dyndns_host: bool,
    force_file_cache_renewal: bool,
) -> HostAddress:
    """This function *may* look up an IP address, or return a host name"""
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns

    if override_dns:
        return override_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    if simulation_mode or _enforce_localhost or is_snmp_usewalk_host:
        return _local_ip_for(family)

    # check if IP address is hard coded by the user
    if configured_ip_address:
        return configured_ip_address

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if is_dyndns_host:
        return host_name

    return cached_dns_lookup(
        host_name,
        family=family,
        force_file_cache_renewal=force_file_cache_renewal,
    )


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(
    hostname: HostName | HostAddress,
    *,
    family: socket.AddressFamily,
    force_file_cache_renewal: bool,
) -> HostAddress:
    """Cached DNS lookup in *two* caching layers

    1) outer layer (this function):
       A *config cache* that caches all calls until the configuration is changed or runtime ends.
       Other than activating a changed configuration there is no way to remove cached results during
       runtime. Changes made by a differend process will not be noticed.

    2) inner layer: see _file_cached_dns_lookup
    """
    cache: dict[
        tuple[HostName | HostAddress, socket.AddressFamily], HostAddress | MKIPAddressLookupError
    ] = cache_manager.obtain_cache("cached_dns_lookup")
    cache_id = hostname, family

    # Address has already been resolved in prior call to this function?
    try:
        if isinstance(prior_result := cache[cache_id], HostAddress):
            return prior_result
        raise prior_result
    except KeyError:
        pass

    try:
        ip_address = _file_cached_dns_lookup(
            hostname,
            family,
            force_file_cache_renewal=force_file_cache_renewal,
        )
    except MKIPAddressLookupError as exc:
        cache[cache_id] = exc
        raise

    cache[cache_id] = ip_address
    return ip_address


def _file_cached_dns_lookup(
    hostname: HostName | HostAddress,
    family: socket.AddressFamily,
    *,
    force_file_cache_renewal: bool,
) -> HostAddress:
    # TODO: is there any point in the IPLookupCache being cached in the
    # *config cache*?
    # It seems to me it could well be kept during the entire runtime.
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
        console.verbose(f"Updating {family_str} DNS cache for {hostname}: {ipa}")
        ip_lookup_cache[cache_id] = ipa

    return ipa


def _actual_dns_lookup(
    *,
    host_name: HostName | HostAddress,
    family: socket.AddressFamily,
    fallback: HostAddress | None = None,
) -> HostAddress:
    try:
        socket_address = socket.getaddrinfo(host_name, None, family)[0][4][0]
        if isinstance(socket_address, int):
            raise Exception("Your Python has been compiled with --disable-ipv6, sorry...")
        return HostAddress(socket_address)
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
            (
                (HostName(k), socket.AF_INET)  # old pre IPv6 style
                if isinstance(k, str)
                else (HostName(k[0]), {4: socket.AF_INET, 6: socket.AF_INET6}[k[1]])
            ): HostAddress(v)
            for k, v in loaded_object.items()
        }


class IPLookupCache:
    PATH = cmk.utils.paths.var_dir / "ipaddresses.cache"

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
            if cmk.ccc.debug.enabled():
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
    if "ip_lookup" in cache_manager:
        # Return already created and initialized cache
        return IPLookupCache(cache_manager.obtain_cache("ip_lookup"))

    cache = IPLookupCache(cache_manager.obtain_cache("ip_lookup"))
    cache.load_persisted()
    return cache


def update_dns_cache(
    *,
    hosts: Iterable[HostName],
    ip_lookup_config: IPLookupConfig,
) -> tuple[int, Sequence[HostName]]:
    failed = []

    ip_lookup_cache = _get_ip_lookup_cache()

    with ip_lookup_cache.persisting_disabled():
        console.verbose("Cleaning up existing DNS cache...")
        ip_lookup_cache.clear()

        console.verbose("Updating DNS cache...")
        # `_annotate_family()` handles DUAL_STACK and NO_IP
        for host_name, family in _annotate_family(hosts, ip_lookup_config):
            console.verbose_no_lf(f"{host_name} ({family})...")
            try:
                ip = _lookup_ip_address(
                    host_name=host_name,
                    family=family,
                    configured_ip_address=(
                        ip_lookup_config.ipv4_addresses
                        if family is socket.AF_INET
                        else ip_lookup_config.ipv6_addresses
                    ).get(host_name),
                    simulation_mode=ip_lookup_config.simulation_mode,
                    is_snmp_usewalk_host=(
                        ip_lookup_config.is_use_walk_host(host_name)
                        and ip_lookup_config.is_snmp_host(host_name)
                    ),
                    override_dns=ip_lookup_config.fake_dns,
                    is_dyndns_host=ip_lookup_config.is_dyndns_host(host_name),
                    force_file_cache_renewal=True,  # it's cleared anyway
                )
                console.verbose(f"{ip}")

            except (MKTerminate, MKTimeout):
                # We should be more specific with the exception handler below, then we
                # could drop this special handling here
                raise
            except MKIPAddressLookupError as e:
                failed.append(host_name)
                console.verbose(f"lookup failed: {e}")
                continue
            except Exception as e:
                failed.append(host_name)
                console.verbose(f"lookup failed: {e}")
                if cmk.ccc.debug.enabled():
                    raise
                continue

    ip_lookup_cache.save_persisted()

    return len(ip_lookup_cache), failed


def _annotate_family(
    hosts: Iterable[HostName],
    ip_lookup_config: IPLookupConfig,
) -> Iterable[
    tuple[
        HostName,
        Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ]
]:
    for host_name in hosts:
        ip_stack_config = ip_lookup_config.ip_stack_config(host_name)
        if IPStackConfig.IPv4 in ip_stack_config:
            yield host_name, socket.AddressFamily.AF_INET
        if IPStackConfig.IPv6 in ip_stack_config:
            yield host_name, socket.AddressFamily.AF_INET6


class CollectFailedHosts:
    """Collects hosts for which IP lookup fails"""

    def __init__(self) -> None:
        self._failed_ip_lookups: dict[HostName, Exception] = {}

    @property
    def failed_ip_lookups(self) -> Mapping[HostName, Exception]:
        return self._failed_ip_lookups

    def __call__(self, host_name: HostName, exc: Exception) -> None:
        self._failed_ip_lookups[host_name] = exc

    def format_errors(self) -> Sequence[str]:
        return [
            (
                f"Cannot lookup IP address of '{host}' ({exc}). "
                "The host will not be monitored correctly."
            )
            for host, exc in self.failed_ip_lookups.items()
        ]
