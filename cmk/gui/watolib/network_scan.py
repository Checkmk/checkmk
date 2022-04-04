#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The WATO folders network scan for new hosts"""

import re
import socket
import subprocess
import threading
import time
import traceback
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, TYPE_CHECKING

from cmk.utils import store
from cmk.utils.translations import translate_hostname
from cmk.utils.type_defs import HostAddress, HostName

from cmk.gui import userdb
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import UserContext
from cmk.gui.site_config import get_site_config, is_wato_slave_site, site_is_local
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.hosts_and_folders import Folder, Host, update_metadata

NetworkScanFoundHosts = List[Tuple[HostName, HostAddress]]
NetworkScanResult = Dict[str, Any]


class NetworkScanRequest(NamedTuple):
    folder_path: str


if TYPE_CHECKING:
    from cmk.gui.watolib.hosts_and_folders import CREFolder


def execute_network_scan_job() -> None:
    """Executed by the multisite cron job once a minute. Is only executed in the
    central site. Finds the next folder to scan and starts it via WATO
    automation. The result is written to the folder in the master site."""
    if is_wato_slave_site():
        return  # Don't execute this job on slaves.

    folder = _find_folder_to_scan()
    if not folder:
        return  # Nothing to do.

    run_as = folder.attribute("network_scan")["run_as"]
    if not userdb.user_exists(run_as):
        raise MKGeneralException(
            _("The user %s used by the network " "scan of the folder %s does not exist.")
            % (run_as, folder.title())
        )

    with UserContext(run_as):
        result: NetworkScanResult = {
            "start": time.time(),
            "end": True,  # means currently running
            "state": None,
            "output": "The scan is currently running.",
        }

        # Mark the scan in progress: Is important in case the request takes longer than
        # the interval of the cron job (1 minute). Otherwise the scan might be started
        # a second time before the first one finished.
        _save_network_scan_result(folder, result)

        try:
            if site_is_local(folder.site_id()):
                found = _do_network_scan(folder)
            else:
                found = do_remote_automation(
                    get_site_config(folder.site_id()), "network-scan", [("folder", folder.path())]
                )

            if not isinstance(found, list):
                raise MKGeneralException(_("Received an invalid network scan result: %r") % found)

            _add_scanned_hosts_to_folder(folder, found)

            result.update(
                {
                    "state": True,
                    "output": _("The network scan found %d new hosts.") % len(found),
                }
            )
        except Exception as e:
            result.update(
                {
                    "state": False,
                    "output": _("An exception occured: %s") % e,
                }
            )
            logger.error("Exception in network scan:\n%s", traceback.format_exc())

        result["end"] = time.time()

        _save_network_scan_result(folder, result)


def _find_folder_to_scan() -> Optional["CREFolder"]:
    """Find the folder which network scan is longest waiting and return the folder object."""
    folder_to_scan = None
    for folder in Folder.all_folders().values():
        scheduled_time = folder.next_network_scan_at()
        if scheduled_time is not None and scheduled_time < time.time():
            if folder_to_scan is None:
                folder_to_scan = folder
            elif folder_to_scan.next_network_scan_at() > folder.next_network_scan_at():
                folder_to_scan = folder
    return folder_to_scan


def _add_scanned_hosts_to_folder(folder: "CREFolder", found: NetworkScanFoundHosts) -> None:
    network_scan_properties = folder.attribute("network_scan")

    translation = network_scan_properties.get("translate_names", {})

    entries = []
    for host_name, ipaddr in found:
        host_name = translate_hostname(translation, host_name)

        attrs = update_metadata({}, created_by=_("Network scan"))

        if "tag_criticality" in network_scan_properties:
            attrs["tag_criticality"] = network_scan_properties.get("tag_criticality", "offline")

        if network_scan_properties.get("set_ipaddress", True):
            attrs["ipaddress"] = ipaddr

        if not Host.host_exists(host_name):
            entries.append((host_name, attrs, None))

    with store.lock_checkmk_configuration():
        folder.create_hosts(entries)
        folder.save()


def _save_network_scan_result(folder: "CREFolder", result: NetworkScanResult) -> None:
    # Reload the folder, lock WATO before to protect against concurrency problems.
    with store.lock_checkmk_configuration():
        # A user might have changed the folder somehow since starting the scan. Load the
        # folder again to get the current state.
        write_folder = Folder.folder(folder.path())
        write_folder.set_attribute("network_scan_result", result)
        write_folder.save()


@automation_command_registry.register
class AutomationNetworkScan(AutomationCommand):
    def command_name(self):
        return "network-scan"

    def get_request(self) -> NetworkScanRequest:
        folder_path = request.var("folder")
        if folder_path is None:
            raise MKGeneralException(_("Folder path is missing"))
        return NetworkScanRequest(folder_path=folder_path)

    def execute(self, api_request):
        folder = Folder.folder(api_request.folder_path)
        return _do_network_scan(folder)


# This is executed in the site the host is assigned to.
# A list of tuples is returned where each tuple represents a new found host:
# [(hostname, ipaddress), ...]
def _do_network_scan(folder):
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
    addresses = set()

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

    addresses: List[HostAddress] = []

    if first_int > last_int:
        return addresses  # skip wrong config

    while first_int <= last_int:
        addresses.append(_string_from_ip_int(first_int))
        first_int += 1
        if first_int - 1 == _FULL_IPV4:  # stop on last IPv4 address
            break

    return addresses


def _ip_int_from_string(ip_str: str) -> int:
    packed_ip = 0
    octets = ip_str.split(".")
    for oc in octets:
        packed_ip = (packed_ip << 8) | int(oc)
    return packed_ip


def _string_from_ip_int(ip_int: int) -> HostAddress:
    octets: List[str] = []
    for _unused in range(4):
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

    for host in Host.all().values():
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
        folder.attribute("network_scan").get("max_parallel_pings", 100), num_addresses
    )

    # Initalize all workers
    threads = []
    found_hosts: List[Tuple[HostName, HostAddress]] = []
    for _t_num in range(parallel_pings):
        t = threading.Thread(target=_ping_worker, args=[ip_addresses, found_hosts])
        t.daemon = True
        threads.append(t)
        t.start()

    # Now wait for all workers to finish
    for t in threads:
        t.join()

    return found_hosts


def _ping_worker(addresses: List[HostAddress], hosts: List[Tuple[HostName, HostAddress]]) -> None:
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


def _ping(address: HostAddress) -> bool:
    return (
        subprocess.Popen(
            ["ping", "-c2", "-w2", address],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            close_fds=True,
        ).wait()
        == 0
    )
