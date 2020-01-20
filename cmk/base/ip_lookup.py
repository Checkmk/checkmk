#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import socket
import errno
import os
from typing import (  # pylint: disable=unused-import
    Optional, Dict, Tuple, Union, List, cast,
)

import cmk.utils.paths
import cmk.utils.debug
import cmk.utils.store as store
from cmk.utils.exceptions import MKTimeout, MKTerminate

import cmk.base
import cmk.base.console as console
import cmk.base.config as config
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, HostAddress)
from cmk.base.exceptions import MKIPAddressLookupError

IPLookupCacheId = Tuple[HostName, int]
NewIPLookupCache = Dict[IPLookupCacheId, str]
LegacyIPLookupCache = Dict[str, str]
UpdateDNSCacheResult = Tuple[int, List[HostName]]

_fake_dns = None  # type: Optional[HostAddress]
_enforce_localhost = False


def enforce_fake_dns(address):
    # type: (HostAddress) -> None
    global _fake_dns
    _fake_dns = address


def enforce_localhost():
    # type: () -> None
    global _enforce_localhost
    _enforce_localhost = True


def lookup_ipv4_address(hostname):
    # type: (HostName) -> Optional[str]
    return lookup_ip_address(hostname, 4)


def lookup_ipv6_address(hostname):
    # type: (HostName) -> Optional[str]
    return lookup_ip_address(hostname, 6)


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(hostname, family=None):
    # type: (HostName, Optional[int]) -> Optional[str]
    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns
    if config.fake_dns:
        return config.fake_dns

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    if family is None:  # choose primary family
        family = 6 if host_config.is_ipv6_primary else 4

    # Honor simulation mode und usewalk hosts. Never contact the network.
    if config.simulation_mode or _enforce_localhost or \
         (host_config.is_usewalk_host and host_config.is_snmp_host):
        if family == 4:
            return "127.0.0.1"

        return "::1"

    # Now check, if IP address is hard coded by the user
    if family == 4:
        ipa = config.ipaddresses.get(hostname)
    else:
        ipa = config.ipv6addresses.get(hostname)

    if ipa:
        return ipa

    # Hosts listed in dyndns hosts always use dynamic DNS lookup.
    # The use their hostname as IP address at all places
    if config_cache.in_binary_hostlist(hostname, config.dyndns_hosts):
        return hostname

    return cached_dns_lookup(hostname, family)


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(hostname, family):
    # type: (HostName, int) -> Optional[str]
    cache = cmk.base.config_cache.get_dict("cached_dns_lookup")
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

    host_config = config.get_config_cache().get_host_config(hostname)

    if host_config.is_no_ip_host:
        cache[cache_id] = None
        return None

    # Now do the actual DNS lookup
    try:
        ipa = socket.getaddrinfo(hostname, None, family == 4 and socket.AF_INET or
                                 socket.AF_INET6)[0][4][0]

        # Update our cached address if that has changed or was missing
        if ipa != cached_ip:
            console.verbose("Updating IPv%d DNS cache for %s: %s\n" % (family, hostname, ipa))
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
        else:
            cache[cache_id] = None
            raise MKIPAddressLookupError("Failed to lookup IPv%d address of %s via DNS: %s" %
                                         (family, hostname, e))


class IPLookupCache(cmk.base.caching.DictCache):
    def __init__(self):
        # type: () -> None
        super(IPLookupCache, self).__init__()
        self.persist_on_update = True

    def load_persisted(self):
        # type: () -> None
        try:
            self.update(_load_ip_lookup_cache(lock=False))
        except (MKTerminate, MKTimeout):
            # We should be more specific with the exception handler below, then we
            # could drop this special handling here
            raise

        except Exception:
            if cmk.utils.debug.enabled():
                raise
            # TODO: Would be better to log it somewhere to make the failure transparent

    def update_cache(self, cache_id, ipa):
        # type: (IPLookupCacheId, str) -> None
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
            self[cache_id] = ipa
            return

        try:
            self.update(_load_ip_lookup_cache(lock=True))
            self[cache_id] = ipa
            self.save_persisted()
        finally:
            store.release_lock(_cache_path())

    def save_persisted(self):
        # type: () -> None
        store.save_object_to_file(_cache_path(), self, pretty=False)


def _get_ip_lookup_cache():
    # type: () -> IPLookupCache
    """A file based fall-back DNS cache in case resolution fails"""
    if cmk.base.config_cache.exists("ip_lookup"):
        # Return already created and initialized cache
        return cast(IPLookupCache, cmk.base.config_cache.get("ip_lookup", IPLookupCache))

    cache = cast(IPLookupCache, cmk.base.config_cache.get("ip_lookup", IPLookupCache))
    cache.load_persisted()
    return cache


def _load_ip_lookup_cache(lock):
    # type: (bool) -> NewIPLookupCache
    return _convert_legacy_ip_lookup_cache(
        store.load_object_from_file(_cache_path(), default={}, lock=lock))


def _convert_legacy_ip_lookup_cache(cache):
    # type: (Union[LegacyIPLookupCache, NewIPLookupCache]) -> NewIPLookupCache
    """be compatible to old caches which were created by Check_MK without IPv6 support"""
    if not cache:
        return {}

    # New version has (hostname, ip family) as key
    if isinstance(list(cache.keys())[0], tuple):
        return cast(NewIPLookupCache, cache)

    cache = cast(LegacyIPLookupCache, cache)

    new_cache = {}  # type: NewIPLookupCache
    for key, val in cache.items():
        new_cache[(key, 4)] = val
    return new_cache


def _cache_path():
    # type: () -> str
    return cmk.utils.paths.var_dir + "/ipaddresses.cache"


def update_dns_cache():
    # type: () -> UpdateDNSCacheResult
    failed = []

    ip_lookup_cache = _get_ip_lookup_cache()
    ip_lookup_cache.persist_on_update = False

    console.verbose("Cleaning up existing DNS cache...\n")
    _clear_ip_lookup_cache(ip_lookup_cache)

    console.verbose("Updating DNS cache...\n")
    for hostname, family in _get_dns_cache_lookup_hosts():
        console.verbose("%s (IPv%d)..." % (hostname, family))
        try:
            ip = lookup_ip_address(hostname, family)
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


def _clear_ip_lookup_cache(ip_lookup_cache):
    # type: (IPLookupCache) -> None
    """Clear the persisted AND in memory cache"""
    try:
        os.unlink(_cache_path())
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    ip_lookup_cache.clear()


def _get_dns_cache_lookup_hosts():
    # type: () -> List[IPLookupCacheId]
    config_cache = config.get_config_cache()
    hosts = []
    for hostname in config_cache.all_active_hosts():
        host_config = config_cache.get_host_config(hostname)

        if host_config.is_ipv4_host:
            hosts.append((hostname, 4))

        if host_config.is_ipv6_host:
            hosts.append((hostname, 6))

    return hosts
