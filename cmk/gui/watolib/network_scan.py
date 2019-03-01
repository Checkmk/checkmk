#!/usr/bin/python
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
"""The WATO folders network scan for new hosts"""

import os
import re
import threading
import socket
import subprocess
from typing import NamedTuple  # pylint: disable=unused-import

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    Host,
)
from cmk.gui.watolib.automation_commands import (
    AutomationCommand,
    automation_command_registry,
)

NetworkScanRequest = NamedTuple("NetworkScanRequest", [("folder_path", str)])


@automation_command_registry.register
class AutomationNetworkScan(AutomationCommand):
    def command_name(self):
        return "network-scan"

    def get_request(self):
        # type: () -> NetworkScanRequest
        folder_path = html.request.var("folder")
        if folder_path is None:
            raise MKGeneralException(_("Folder path is missing"))
        return NetworkScanRequest(folder_path=folder_path)

    def execute(self, request):
        folder = Folder.folder(request.folder_path)
        return do_network_scan(folder)


# This is executed in the site the host is assigned to.
# A list of tuples is returned where each tuple represents a new found host:
# [(hostname, ipaddress), ...]
def do_network_scan(folder):
    ip_addresses = _ip_addresses_to_scan(folder)
    return _scan_ip_addresses(folder, ip_addresses)


def _ip_addresses_to_scan(folder):
    ip_range_specs = folder.attribute("network_scan")["ip_ranges"]
    exclude_specs = folder.attribute("network_scan")["exclude_ranges"]

    to_scan = _ip_addresses_of_ranges(ip_range_specs)
    exclude = _ip_addresses_of_ranges(exclude_specs)

    # Remove excludes from to_scan list
    to_scan.difference_update(exclude)

    # Reduce by all known host addresses
    # FIXME/TODO: Shouldn't this filtering be done on the central site?
    to_scan.difference_update(_known_ip_addresses())

    # And now apply the IP regex patterns to exclude even more addresses
    to_scan.difference_update(_excludes_by_regexes(to_scan, exclude_specs))

    return to_scan


def _ip_addresses_of_ranges(ip_ranges):
    addresses = set([])

    for ty, spec in ip_ranges:
        if ty == "ip_range":
            addresses.update(_ip_addresses_of_range(spec))

        elif ty == "ip_network":
            addresses.update(_ip_addresses_of_network(spec))

        elif ty == "ip_list":
            addresses.update(spec)

    return addresses


_FULL_IPV4 = (2**32) - 1


def _ip_addresses_of_range(spec):
    first_int, last_int = map(_ip_int_from_string, spec)

    addresses = []

    if first_int > last_int:
        return addresses  # skip wrong config

    while first_int <= last_int:
        addresses.append(_string_from_ip_int(first_int))
        first_int += 1
        if first_int - 1 == _FULL_IPV4:  # stop on last IPv4 address
            break

    return addresses


def _ip_int_from_string(ip_str):
    packed_ip = 0
    octets = ip_str.split(".")
    for oc in octets:
        packed_ip = (packed_ip << 8) | int(oc)
    return packed_ip


def _string_from_ip_int(ip_int):
    octets = []
    for _ in xrange(4):
        octets.insert(0, str(ip_int & 0xFF))
        ip_int >>= 8
    return ".".join(octets)


def _ip_addresses_of_network(spec):
    net_addr, net_bits = spec

    ip_int = _ip_int_from_string(net_addr)
    mask_int = _mask_bits_to_int(int(net_bits))
    first = ip_int & (_FULL_IPV4 ^ mask_int)
    last = ip_int | (1 << (32 - int(net_bits))) - 1

    return [_string_from_ip_int(i) for i in range(first + 1, last - 1)]


def _mask_bits_to_int(n):
    return (1 << (32 - n)) - 1


# This will not scale well. Do you have a better idea?
def _known_ip_addresses():
    addresses = set()

    for host in Host.all().itervalues():
        attributes = host.attributes()

        address = attributes.get("ipaddress")
        if address:
            addresses.add(address)

        addresses.update(attributes.get("additional_ipv4addresses", []))

    return addresses


def _excludes_by_regexes(addresses, exclude_specs):
    patterns = []
    for ty, spec in exclude_specs:
        if ty == "ip_regex_list":
            for p in spec:
                patterns.append(re.compile(p))

    if not patterns:
        return []

    excludes = []
    for address in addresses:
        for p in patterns:
            if p.match(address):
                excludes.append(address)
                break  # one match is enough, exclude this.

    return excludes


# Start ping threads till max parallel pings let threads do their work till all are done.
# let threds also do name resolution. Return list of tuples (hostname, address).
def _scan_ip_addresses(folder, ip_addresses):
    num_addresses = len(ip_addresses)

    # dont start more threads than needed
    parallel_pings = min(
        folder.attribute("network_scan").get("max_parallel_pings", 100), num_addresses)

    # Initalize all workers
    threads = []
    found_hosts = []
    for _t_num in range(parallel_pings):
        t = threading.Thread(target=_ping_worker, args=[ip_addresses, found_hosts])
        t.daemon = True
        threads.append(t)
        t.start()

    # Now wait for all workers to finish
    for t in threads:
        t.join()

    return found_hosts


def _ping_worker(addresses, hosts):
    while True:
        try:
            ipaddress = addresses.pop()
        except KeyError:
            break

        if _ping(ipaddress):
            try:
                host_name = socket.gethostbyaddr(ipaddress)[0]
            except socket.error:
                host_name = ipaddress

            hosts.append((host_name, ipaddress))


def _ping(address):
    return subprocess.Popen(['ping', '-c2', '-w2', address],
                            stdout=open(os.devnull, "a"),
                            stderr=subprocess.STDOUT,
                            close_fds=True).wait() == 0
