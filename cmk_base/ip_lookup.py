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
from typing import Optional  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.debug
import cmk.utils.store as store

import cmk_base
import cmk_base.console as console
import cmk_base.config as config
from cmk_base.exceptions import MKIPAddressLookupError

_fake_dns = None  # type: Optional[str]
_enforce_localhost = False


def enforce_fake_dns(address):
    global _fake_dns
    _fake_dns = address


def enforce_localhost():
    global _enforce_localhost
    _enforce_localhost = True


def lookup_ipv4_address(hostname):
    # type: (str) -> Optional[str]
    return lookup_ip_address(hostname, 4)


def lookup_ipv6_address(hostname):
    # type: (str) -> Optional[str]
    return lookup_ip_address(hostname, 6)


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(hostname, family=None):
    # type: (str, Optional[int]) -> Optional[str]
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
    # type: (str, int) -> Optional[str]
    cache = cmk_base.config_cache.get_dict("cached_dns_lookup")
    cache_id = hostname, family

    # Address has already been resolved in prior call to this function?
    try:
        return cache[cache_id]
    except KeyError:
        pass

    # Prepare file based fall-back DNS cache in case resolution fails
    # TODO: Find a place where this only called once!
    ip_lookup_cache = _initialize_ip_lookup_cache()

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
            _update_ip_lookup_cache(cache_id, ipa)

        cache[cache_id] = ipa  # Update in-memory-cache
        return ipa

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


def _initialize_ip_lookup_cache():
    # Already created and initialized. Simply return it!
    if cmk_base.config_cache.exists("ip_lookup"):
        return cmk_base.config_cache.get_dict("ip_lookup")

    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")

    try:
        data_from_file = store.load_data_from_file(cmk.utils.paths.var_dir + '/ipaddresses.cache',
                                                   {})
        ip_lookup_cache.update(data_from_file)

        # be compatible to old caches which were created by Check_MK without IPv6 support
        _convert_legacy_ip_lookup_cache(ip_lookup_cache)
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        # TODO: Would be better to log it somewhere to make the failure transparent

    return ip_lookup_cache


def _convert_legacy_ip_lookup_cache(ip_lookup_cache):
    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")
    if not ip_lookup_cache:
        return

    # New version has (hostname, ip family) as key
    if isinstance(ip_lookup_cache.keys()[0], tuple):
        return

    new_cache = {}
    for key, val in ip_lookup_cache.items():
        new_cache[(key, 4)] = val
    ip_lookup_cache.clear()
    ip_lookup_cache.update(new_cache)


def _update_ip_lookup_cache(cache_id, ipa):
    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")

    # Read already known data
    cache_path = _cache_path()
    try:
        data_from_file = cmk.utils.store.load_data_from_file(cache_path, default={}, lock=True)

        _convert_legacy_ip_lookup_cache(data_from_file)
        ip_lookup_cache.update(data_from_file)
        ip_lookup_cache[cache_id] = ipa

        # (I don't like this)
        # TODO: this file always grows... there should be a cleanup mechanism
        #       maybe on "cmk --update-dns-cache"
        # The cache_path is already locked from a previous function call..
        cmk.utils.store.save_data_to_file(cache_path, ip_lookup_cache)
    finally:
        cmk.utils.store.release_lock(cache_path)


def _cache_path():
    return cmk.utils.paths.var_dir + "/ipaddresses.cache"


def update_dns_cache():
    updated = 0
    failed = []

    console.verbose("Cleaning up existing DNS cache...\n")
    try:
        os.unlink(_cache_path())
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    config_cache = config.get_config_cache()

    console.verbose("Updating DNS cache...\n")
    for hostname in config_cache.all_active_hosts():
        host_config = config_cache.get_host_config(hostname)

        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        for family in [4, 6]:
            if (family == 4 and host_config.is_ipv4_host) \
               or (family == 6 and host_config.is_ipv6_host):
                console.verbose("%s (IPv%d)..." % (hostname, family))
                try:
                    if family == 4:
                        ip = lookup_ipv4_address(hostname)
                    else:
                        ip = lookup_ipv6_address(hostname)

                    console.verbose("%s\n" % ip)
                    updated += 1
                except Exception as e:
                    failed.append(hostname)
                    console.verbose("lookup failed: %s\n" % e)
                    if cmk.utils.debug.enabled():
                        raise
                    continue

    return updated, failed
