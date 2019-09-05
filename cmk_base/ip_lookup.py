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

import cmk.debug
import cmk.paths
import cmk.store as store

import cmk_base
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.rulesets as rulesets
from cmk_base.exceptions import MKIPAddressLookupError

_fake_dns = False
_enforce_localhost = False


def enforce_fake_dns(address):
    global _fake_dns
    _fake_dns = address


def enforce_localhost():
    global _enforce_localhost
    _enforce_localhost = True


def lookup_ipv4_address(hostname):
    return lookup_ip_address(hostname, 4)


def lookup_ipv6_address(hostname):
    return lookup_ip_address(hostname, 6)


# Determine the IP address of a host. It returns either an IP address or, when
# a hostname is configured as IP address, the hostname.
# Or raise an exception when a hostname can not be resolved on the first
# try to resolve a hostname. On later tries to resolve a hostname  it
# returns None instead of raising an exception.
# FIXME: This different handling is bad. Clean this up!
def lookup_ip_address(hostname, family=None):
    if family == None:  # choose primary family
        family = config.is_ipv6_primary(hostname) and 6 or 4

    # Quick hack, where all IP addresses are faked (--fake-dns)
    if _fake_dns:
        return _fake_dns
    if config.fake_dns:
        return config.fake_dns

    # Honor simulation mode und usewalk hosts. Never contact the network.
    elif config.simulation_mode or _enforce_localhost or \
         (config.is_usewalk_host(hostname) and config.is_snmp_host(hostname)):
        if family == 4:
            return "127.0.0.1"
        else:
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
    if rulesets.in_binary_hostlist(hostname, config.dyndns_hosts):
        return hostname

    return cached_dns_lookup(hostname, family)


# Variables needed during the renaming of hosts (see automation.py)
def cached_dns_lookup(hostname, family):
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

    if config.is_no_ip_host(hostname):
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

    except Exception, e:
        # DNS failed. Use cached IP address if present, even if caching
        # is disabled.
        if cached_ip:
            cache[cache_id] = cached_ip
            return cached_ip
        else:
            cache[cache_id] = None
            raise MKIPAddressLookupError(
                "Failed to lookup IPv%d address of %s via DNS: %s" % (family, hostname, e))


def _initialize_ip_lookup_cache():
    # Already created and initialized. Simply return it!
    if cmk_base.config_cache.exists("ip_lookup"):
        return cmk_base.config_cache.get_dict("ip_lookup")

    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")

    try:
        data_from_file = store.load_data_from_file(cmk.paths.var_dir + '/ipaddresses.cache', {})
        ip_lookup_cache.update(data_from_file)

        # be compatible to old caches which were created by Check_MK without IPv6 support
        _convert_legacy_ip_lookup_cache(ip_lookup_cache)
    except:
        if cmk.debug.enabled():
            raise
        # TODO: Would be better to log it somewhere to make the failure transparent
        pass

    return ip_lookup_cache


def _convert_legacy_ip_lookup_cache(ip_lookup_cache):
    ip_lookup_cache = cmk_base.config_cache.get_dict("ip_lookup")
    if not ip_lookup_cache:
        return

    # New version has (hostname, ip family) as key
    if type(ip_lookup_cache.keys()[0]) == tuple:
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
        data_from_file = cmk.store.load_data_from_file(cache_path, default={}, lock=True)

        _convert_legacy_ip_lookup_cache(data_from_file)
        ip_lookup_cache.update(data_from_file)
        ip_lookup_cache[cache_id] = ipa

        # (I don't like this)
        # TODO: this file always grows... there should be a cleanup mechanism
        #       maybe on "cmk --update-dns-cache"
        # The cache_path is already locked from a previous function call..
        cmk.store.save_data_to_file(cache_path, ip_lookup_cache)
    finally:
        cmk.store.release_lock(cache_path)


def _cache_path():
    return cmk.paths.var_dir + '/ipaddresses.cache'


def update_dns_cache():
    updated = 0
    failed = []

    console.verbose("Cleaning up existing DNS cache...\n")
    try:
        os.unlink(_cache_path())
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    console.verbose("Updating DNS cache...\n")
    for hostname in config.all_active_hosts():
        # Use intelligent logic. This prevents DNS lookups for hosts
        # with statically configured addresses, etc.
        for family in [4, 6]:
            if (family == 4 and config.is_ipv4_host(hostname)) \
               or (family == 6 and config.is_ipv6_host(hostname)):
                console.verbose("%s (IPv%d)..." % (hostname, family))
                try:
                    if family == 4:
                        ip = lookup_ipv4_address(hostname)
                    else:
                        ip = lookup_ipv6_address(hostname)

                    console.verbose("%s\n" % ip)
                    updated += 1
                except Exception, e:
                    failed.append(hostname)
                    console.verbose("lookup failed: %s\n" % e)
                    if cmk.debug.enabled():
                        raise
                    continue

    return updated, failed
