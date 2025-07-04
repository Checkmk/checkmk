#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Setup folders network scan for new hosts"""

import re
import socket
import subprocess
import threading
import time
import traceback
from collections.abc import Sequence
from datetime import timedelta
from typing import Literal, NamedTuple, override, TypeGuard

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.user import UserId

from cmk.utils.paths import configuration_lockfile
from cmk.utils.translations import translate_hostname, TranslationOptions

from cmk.gui import userdb
from cmk.gui.config import Config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.session import UserContext
from cmk.gui.site_config import is_wato_slave_site, site_is_local

from . import bakery, builtin_attributes
from .automation_commands import AutomationCommand, AutomationCommandRegistry
from .automations import do_remote_automation, RemoteAutomationConfig
from .host_attributes import (
    ExcludeIPRange,
    HostAttributeRegistry,
    HostAttributes,
    IPRange,
    NetworkScanResult,
)
from .hosts_and_folders import Folder, folder_tree, Host, update_metadata

NetworkScanFoundHosts = list[tuple[HostName, HostAddress]]


class NetworkScanRequest(NamedTuple):
    folder_path: str


def execute_network_scan_job(config: Config) -> None:
    """Executed by the multisite cron job once a minute. Is only executed in the
    central site. Finds the next folder to scan and starts it via WATO
    automation. The result is written to the folder in the master site."""
    if is_wato_slave_site():
        return  # Don't execute this job on slaves.

    folder = _find_folder_to_scan()
    if not folder:
        return  # Nothing to do.

    run_as = UserId(folder.attributes["network_scan"]["run_as"])
    if not userdb.user_exists(run_as):
        raise MKGeneralException(
            _("The user %s used by the network scan of the folder %s does not exist.")
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
            if site_is_local(site_config := config.sites[folder.site_id()]):
                found = _do_network_scan(folder)
            else:
                raw_response = do_remote_automation(
                    RemoteAutomationConfig.from_site_config(site_config),
                    "network-scan",
                    [("folder", folder.path())],
                    debug=config.debug,
                )
                assert isinstance(raw_response, list)
                found = raw_response

            if not isinstance(found, list):
                raise MKGeneralException(_("Received an invalid network scan result: %r") % found)

            _add_scanned_hosts_to_folder(
                folder,
                found,
                run_as,
                pprint_value=config.wato_pprint_config,
                debug=config.debug,
            )

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
                    "output": _("An exception occurred: %s") % e,
                }
            )
            logger.error("Exception in network scan:\n%s", traceback.format_exc())

        result["end"] = time.time()

        _save_network_scan_result(folder, result)


def _find_folder_to_scan() -> Folder | None:
    """Find the folder which network scan is longest waiting and return the folder object."""
    folder_to_scan = None
    for folder in folder_tree().all_folders().values():
        scheduled_time = folder.next_network_scan_at()
        if scheduled_time is not None and scheduled_time < time.time():
            if folder_to_scan is None:
                folder_to_scan = folder
            elif (at := folder_to_scan.next_network_scan_at()) is not None and at > scheduled_time:
                folder_to_scan = folder
    return folder_to_scan


def _add_scanned_hosts_to_folder(
    folder: Folder,
    found: NetworkScanFoundHosts,
    username: UserId,
    *,
    pprint_value: bool,
    debug: bool,
) -> None:
    if (network_scan_properties := folder.attributes.get("network_scan")) is None:
        return

    translate_names = network_scan_properties.get("translate_names")
    if translate_names is None:
        translation = TranslationOptions({})
    else:
        translation = TranslationOptions(
            {
                "case": translate_names.get("case"),
                "mapping": translate_names.get("mapping", []),
                "drop_domain": translate_names.get("drop_domain", False),
                "regex": translate_names.get("regex", []),
            }
        )

    entries = []
    for host_name, ipaddr in found:
        host_name = translate_hostname(translation, host_name)

        attrs = update_metadata(HostAttributes(), created_by=username)

        if "tag_criticality" in network_scan_properties:
            attrs["tag_criticality"] = network_scan_properties.get("tag_criticality", "offline")

        if network_scan_properties.get("set_ipaddress", True):
            attrs["ipaddress"] = ipaddr

        if not Host.host_exists(host_name):
            entries.append((host_name, attrs, None))

    with store.lock_checkmk_configuration(configuration_lockfile):
        folder.create_hosts(entries, pprint_value=pprint_value)
        folder.save_folder_attributes()
        folder_tree().invalidate_caches()

    bakery.try_bake_agents_for_hosts(tuple(e[0] for e in entries), debug=debug)


def _save_network_scan_result(folder: Folder, result: NetworkScanResult) -> None:
    # Reload the folder, lock Setup before to protect against concurrency problems.
    with store.lock_checkmk_configuration(configuration_lockfile):
        # A user might have changed the folder somehow since starting the scan. Load the
        # folder again to get the current state.
        write_folder = folder_tree().folder(folder.path())
        write_folder.attributes["network_scan_result"] = result
        write_folder.save_folder_attributes()
        folder_tree().invalidate_caches()


class AutomationNetworkScan(AutomationCommand[NetworkScanRequest]):
    @override
    def command_name(self) -> str:
        return "network-scan"

    @override
    def get_request(self) -> NetworkScanRequest:
        folder_path = request.var("folder")
        if folder_path is None:
            raise MKGeneralException(_("Folder path is missing"))
        return NetworkScanRequest(folder_path=folder_path)

    @override
    def execute(self, api_request: NetworkScanRequest) -> list[tuple[HostName, HostAddress]]:
        folder = folder_tree().folder(api_request.folder_path)
        return _do_network_scan(folder)


def register(
    host_attribute_registry: HostAttributeRegistry,
    automation_command_registry: AutomationCommandRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    host_attribute_registry.register(builtin_attributes.HostAttributeNetworkScan)
    host_attribute_registry.register(builtin_attributes.HostAttributeNetworkScanResult)
    automation_command_registry.register(AutomationNetworkScan)
    cron_job_registry.register(
        CronJob(
            name="execute_network_scan_job",
            callable=execute_network_scan_job,
            interval=timedelta(minutes=1),
            run_in_thread=True,
        )
    )


# This is executed in the site the host is assigned to.
def _do_network_scan(folder: Folder) -> list[tuple[HostName, HostAddress]]:
    ip_addresses = _ip_addresses_to_scan(folder)
    return _scan_ip_addresses(folder, ip_addresses)


def _ip_addresses_to_scan(folder: Folder) -> set[HostAddress]:
    ip_range_specs = folder.attributes["network_scan"]["ip_ranges"]
    exclude_specs = folder.attributes["network_scan"]["exclude_ranges"]

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


def _ip_addresses_of_ranges(ip_ranges: list[IPRange] | list[ExcludeIPRange]) -> set[HostAddress]:
    addresses = set()

    for ip_range in ip_ranges:
        # Silently skip unhandled type ip_regex_list for excludes
        if _type_guard_ip_range(ip_range):
            addresses.update(_ip_addresses_of_range(ip_range[1]))

        elif _type_guard_ip_network(ip_range):
            addresses.update(_ip_addresses_of_network(ip_range[1]))

        elif _type_guard_ip_list(ip_range):
            addresses.update(ip_range[1])

    return addresses


def _type_guard_ip_range(
    spec: IPRange | ExcludeIPRange,
) -> TypeGuard[tuple[Literal["ip_range"], tuple[str, str]]]:
    return spec[0] == "ip_range"


def _type_guard_ip_network(
    spec: IPRange | ExcludeIPRange,
) -> TypeGuard[tuple[Literal["ip_network"], tuple[str, int]]]:
    return spec[0] == "ip_network"


def _type_guard_ip_list(
    spec: IPRange | ExcludeIPRange,
) -> TypeGuard[tuple[Literal["ip_list"], Sequence[HostAddress]]]:
    return spec[0] == "ip_list"


_FULL_IPV4 = (2**32) - 1


def _ip_addresses_of_range(spec: tuple[str, str]) -> list[HostAddress]:
    first_int, last_int = map(_ip_int_from_string, spec)

    addresses: list[HostAddress] = []

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
    octets: list[str] = []
    for _unused in range(4):
        octets.insert(0, str(ip_int & 0xFF))
        ip_int >>= 8
    return HostAddress(".".join(octets))


def _ip_addresses_of_network(spec: tuple[str, int]) -> list[HostAddress]:
    net_addr, net_bits = spec

    ip_int = _ip_int_from_string(net_addr)
    mask_int = _mask_bits_to_int(int(net_bits))
    first = ip_int & (_FULL_IPV4 ^ mask_int)
    last = ip_int | (1 << (32 - int(net_bits))) - 1

    return [_string_from_ip_int(i) for i in range(first + 1, last - 1)]


def _mask_bits_to_int(n: int) -> int:
    return (1 << (32 - n)) - 1


# This will not scale well. Do you have a better idea?
def _known_ip_addresses() -> set[HostAddress]:
    addresses = set()

    for host in Host.all().values():
        attributes = host.attributes

        address = attributes.get("ipaddress")
        if address:
            addresses.add(address)

        addresses.update(attributes.get("additional_ipv4addresses", []))

    return addresses


def _excludes_by_regexes(
    addresses: set[HostAddress],
    exclude_specs: list[IPRange | tuple[Literal["ip_regex_list"], Sequence[str]]],
) -> list[HostAddress]:
    patterns = []
    for ty, spec in exclude_specs:
        if ty == "ip_regex_list":
            for p in spec:
                assert isinstance(p, str)
                patterns.append(re.compile(p))

    if not patterns:
        return []

    excludes = []
    for address in addresses:
        for p2 in patterns:
            if p2.match(address):
                excludes.append(address)
                break  # one match is enough, exclude this.

    return excludes


# Start ping threads till max parallel pings let threads do their work till all are done.
# let threds also do name resolution. Return list of tuples (hostname, address).
def _scan_ip_addresses(
    folder: Folder, ip_addresses: set[HostAddress]
) -> list[tuple[HostName, HostAddress]]:
    num_addresses = len(ip_addresses)

    # dont start more threads than needed
    parallel_pings = min(
        folder.attributes["network_scan"].get("max_parallel_pings", 100), num_addresses
    )

    # Initalize all workers
    threads = []
    found_hosts: list[tuple[HostName, HostAddress]] = []
    for _t_num in range(parallel_pings):
        t = threading.Thread(target=_ping_worker, args=[ip_addresses, found_hosts])
        t.daemon = True
        threads.append(t)
        t.start()

    # Now wait for all workers to finish
    for t in threads:
        t.join()

    return found_hosts


def _ping_worker(
    addresses: list[HostAddress], hosts: list[tuple[HostName | HostAddress, HostAddress]]
) -> None:
    while True:
        try:
            ipaddress = addresses.pop()
        except KeyError:
            break

        if _ping(ipaddress):
            try:
                host_name: HostName | HostAddress = HostName(socket.gethostbyaddr(ipaddress)[0])
            except OSError:
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
