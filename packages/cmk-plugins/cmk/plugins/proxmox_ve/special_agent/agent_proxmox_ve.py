#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_proxmox_ve

Checkmk special agent for monitoring Proxmox VE.
Currently reporting the following information about VMs and nodes:
- backup (success, start, duration, volume, bandwidth)
- disk usage
- node info
- mem usage
- time of snapshots
- not yet: replication Status VMs & Container, Gesamtstatus + piggybacked
- not yet: backup summary
- not yet: snapshot_status
- not yet: snapshot_summary

# Read:
# - https://pve.proxmox.com/wiki/Proxmox_VE_API
# - https://pve.proxmox.com/pve-docs/api-viewer/
# - https://pve.proxmox.com/pve-docs/api-viewer/apidoc.js
# - https://pypi.org/project/proxmoxer/
"""

import argparse
import json
import logging
import sys
from collections.abc import Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.plugins.proxmox_ve.lib.ha_manager_status import SectionHaManagerCurrent
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation
from cmk.plugins.proxmox_ve.lib.node_attributes import SectionNodeAttributes
from cmk.plugins.proxmox_ve.lib.node_info import SectionNodeInfo, SubscriptionInfo
from cmk.plugins.proxmox_ve.lib.node_storages import SectionNodeStorages, StorageLink
from cmk.plugins.proxmox_ve.lib.replication import Replication, SectionReplication
from cmk.plugins.proxmox_ve.lib.vm_info import LockState, SectionVMInfo
from cmk.plugins.proxmox_ve.special_agent.libbackups import fetch_backup_data
from cmk.plugins.proxmox_ve.special_agent.libproxmox import CannotRecover, ProxmoxVeAPI
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.6.0b1"

AGENT = "proxmox_ve"

LOGGER = logging.getLogger(f"agent_{AGENT}")

PASSWORD_OPTION = "password"


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    """parse command line arguments and return argument object"""
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )
    parser.add_argument("--timeout", "-t", type=int, default=50, help="API call timeout")
    parser.add_argument("--port", type=int, default=8006, help="IPv4 port to connect to")
    parser.add_argument("--username", "-u", type=str, help="username for connection")
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", required=False, help="password for connection"
    )
    # TODO: warn if log-cutoff-weeks is shorter than actual log length or
    #       shorter than configured check
    parser.add_argument(
        "--log-cutoff-weeks",
        type=int,
        default=2,
        help="Fetch logs N weeks back in time",
    )
    parser.add_argument("--dump-logs", action="store_true", help="dump all backup logs to disk")
    parser.add_argument("--no-cert-check", action="store_true")
    parser.add_argument("hostname", help="Name of the Proxmox VE instance to query.")
    return parser.parse_args(argv)


def find_storage_for_vmid(
    all_vms: Mapping[str, Mapping[str, object]],
    vmid: str,
    config: Mapping[str, str],
) -> MutableMapping[str, MutableSequence[StorageLink]]:
    storage_links: MutableMapping[str, MutableSequence[StorageLink]] = {}

    vm_type = all_vms[vmid].get("type")
    pattern = ("ide", "scsi", "sata", "virtio") if vm_type == "qemu" else ("mp", "rootfs")

    for key, value in config.items():
        if not key.startswith(pattern):
            continue

        storage_name = value.partition(":")[0]
        size = ""
        for part in value.split(","):
            if part.startswith("size="):
                size = part[5:]
                break

        storage_links.setdefault(storage_name, []).append(
            StorageLink(type=key, size=size, vmid=vmid)
        )

    return storage_links


def agent_proxmox_ve_main(args: argparse.Namespace) -> int:
    """Fetches and writes selected information formatted as agent output to stdout"""
    with ProxmoxVeAPI(
        host=args.hostname,
        port=args.port,
        credentials=(
            {
                "username": args.username,
                "password": resolve_secret_option(args, PASSWORD_OPTION).reveal(),
            }
            if args.username
            else {}
        ),
        timeout=args.timeout,
        verify_ssl=not args.no_cert_check,
    ) as session:
        LOGGER.info("Fetch general cluster and node information..")
        data = session.get_tree(
            {
                "cluster": {
                    "backup": [],
                    "resources": [],
                    "replication": [],
                    "status": [],
                    "ha": {
                        "status": {
                            "current": [],
                        }
                    },
                },
                "nodes": [
                    {
                        "{node}": {
                            "subscription": {},
                            # for now just get basic task data - we'll read the logs later
                            "tasks": [],
                            "qemu": [
                                {
                                    "{vmid}": {
                                        "snapshot": [],
                                        "config": {},
                                    }
                                }
                            ],
                            "lxc": [
                                {
                                    "{vmid}": {
                                        "snapshot": [],
                                        "config": {},
                                    }
                                }
                            ],
                            "version": {},
                            "time": {},
                            "replication": [],
                        },
                    }
                ],
                "version": {},
            }
        )

        LOGGER.info("Fetch and process backup logs..")
        logged_backup_data = fetch_backup_data(args, session, data["nodes"])

    all_vms = {
        str(entry["vmid"]): entry
        for entry in data["cluster"]["resources"]
        if entry["type"] in {"lxc", "qemu"} and entry["status"] not in {"unknown"}
    }

    backup_data = {
        # generate list of all VMs IDs - both lxc and qemu
        "vmids": sorted(list(all_vms.keys())),
        # look up scheduled backups and extract assigned VMIDs
        "scheduled_vmids": sorted(
            list(
                {
                    vmid
                    for backup in data["cluster"]["backup"]
                    if "vmid" in backup and backup["enabled"] == "1"
                    for vmid in backup["vmid"].split(",")
                }
            )
        ),  #
        # add data of actually logged VMs
        "logged_vmids": logged_backup_data,
    }

    node_timezones = {}  # Timezones on nodes can be potentially different
    snapshot_data = {}
    config_lock_data = {}

    replications = {
        node["node"]: [rep for rep in node.get("replication", [])] for node in data["nodes"]
    }
    all_storages = {
        entry["id"]: entry for entry in data["cluster"]["resources"] if entry["type"] == "storage"
    }

    ha_manager_status = SectionHaManagerCurrent.from_json_list(
        data["cluster"]["ha"]["status"]["current"]
    )
    cluster_name = next(
        (item["name"] for item in data["cluster"]["status"] if item.get("type") == "cluster"),
        "",
    )
    node_cluster_mapping = {
        item["name"]: cluster_name
        for item in data["cluster"]["status"]
        if item.get("type") == "node" and item.get("name")
    }

    node_storage: MutableMapping[str, MutableMapping[str, MutableSequence[StorageLink]]] = {}
    for node in data["nodes"]:
        if (timezone := node["time"].get("timezone")) is not None:
            node_timezones[node["node"]] = timezone
        # only lxc and qemu can have snapshots
        for vm in node.get("lxc", []) + node.get("qemu", []):
            snapshot_data[str(vm["vmid"])] = {
                "snaptimes": [x["snaptime"] for x in vm["snapshot"] if "snaptime" in x],
            }
            config_lock_data[str(vm["vmid"])] = {
                "lock": vm["config"].get("lock"),
            }
            node_storage[node["node"]] = find_storage_for_vmid(
                all_vms, str(vm["vmid"]), vm["config"]
            )

    def date_to_utc(naive_string: str, tz: str) -> str:
        """
        Adds timezone information to a date string.
        Returns a timezone-aware string
        """
        local_tz = ZoneInfo(tz)
        timezone_unaware = datetime.strptime(naive_string, "%Y-%m-%d %H:%M:%S")
        timezone_aware = timezone_unaware.replace(tzinfo=local_tz)
        return timezone_aware.strftime("%Y-%m-%d %H:%M:%S%z")

    #  overwrite all the start time strings with timezone aware start strings
    for vmid in logged_backup_data:
        try:
            # Happens when the VM has backup data but is not in all_vms
            tz = node_timezones[all_vms[vmid]["node"]]
        except KeyError:
            # get the first value of the first key
            tz = next(iter(node_timezones.values()))
        logged_backup_data[vmid]["started_time"] = date_to_utc(
            logged_backup_data[vmid]["started_time"], tz
        )

    LOGGER.info("all VMs:          %r", backup_data["vmids"])
    LOGGER.info("expected backups: %r", backup_data["scheduled_vmids"])
    LOGGER.info("actual backups:   %r", sorted(list(logged_backup_data.keys())))
    LOGGER.info("snaptimes:        %r", snapshot_data)

    LOGGER.info("Write agent output..")
    for node in data["nodes"]:
        assert node["type"] == "node"
        piggyback_host = "" if args.hostname.startswith(node["node"] + ".") else node["node"]
        sys.stdout.write(f"<<<<{piggyback_host}>>>>\n")
        for name, content in _create_node_sections(
            node,
            all_vms,
            node_cluster_mapping,
            replications,
            all_storages,
            node_storage,
            ha_manager_status,
            data,
        ):
            sys.stdout.write(f"<<<{name}:sep(0)>>>\n{json.dumps(content)}\n")
        if "uptime" in node:
            sys.stdout.write("<<<uptime>>>\n")
            sys.stdout.write(f"{node['uptime']}\n")
        sys.stdout.write("<<<<>>>>\n")

    for vmid, vm in all_vms.items():
        sys.stdout.write(f"<<<<{vm['name'] or ''}>>>>\n")
        for name, content in _create_vm_sections(
            vmid,
            vm,
            config_lock_data,
            logged_backup_data,
            snapshot_data,
            node_cluster_mapping,
        ):
            sys.stdout.write(f"<<<{name}:sep(0)>>>\n{json.dumps(content)}\n")
        sys.stdout.write("<<<<>>>>\n")

    return 0


def _create_node_sections(
    node: Any,
    all_vms: Mapping[str, Mapping[str, Any]],
    node_cluster_mapping: Mapping[str, Any],
    replications: Mapping[str, Any],
    all_storages: Mapping[str, Any],
    node_storage: Mapping[str, Mapping[str, Sequence[StorageLink]]],
    ha_manager_status: SectionHaManagerCurrent,
    data: Any,
) -> Iterable[tuple[str, object]]:
    yield (
        "proxmox_ve_node_info",
        SectionNodeInfo(
            status=node["status"],
            lxc=[str(vmid) for vmid in all_vms if all_vms[vmid]["type"] == "lxc"],
            qemu=[str(vmid) for vmid in all_vms if all_vms[vmid]["type"] == "qemu"],
            version=node["version"].get("version", "n/a"),
            subscription=SubscriptionInfo(
                status=node["subscription"]["status"],
                next_due_date=node["subscription"].get("nextduedate"),
            ),
        ).model_dump(),
    )

    running_vms = [
        vm for vm in all_vms.values() if vm["node"] == node["node"] and vm["status"] == "running"
    ]
    yield (
        "proxmox_ve_node_allocation",
        SectionNodeAllocation(
            status=node["status"],
            node_total_cpu=node["maxcpu"],
            allocated_cpu=sum(vm["maxcpu"] for vm in running_vms),
            node_total_mem=node["maxmem"],
            allocated_mem=sum(vm["maxmem"] for vm in running_vms),
        ).model_dump_json(),
    )

    yield (
        "proxmox_ve_replication",
        SectionReplication(
            node=node["node"],
            cluster=node_cluster_mapping.get(node["node"]),
            replications=[
                Replication(
                    id=repl["id"],
                    source=repl["source"],
                    target=repl["target"],
                    schedule=repl["schedule"],
                    last_sync=repl["last_sync"],
                    last_try=repl["last_try"],
                    next_sync=repl["next_sync"],
                    duration=repl["duration"],
                    error=repl.get("error"),
                )
                for repl in replications.get(node["node"], [])
            ],
            cluster_has_replications=True if data["cluster"]["replication"] else False,
        ).model_dump_json(),
    )

    yield (
        "proxmox_ve_node_storage",
        SectionNodeStorages(
            node=node["node"],
            storages=[
                storage_data
                for storage_data in all_storages.values()
                if storage_data.get("node", "") == node["node"]
            ],
            storage_links=node_storage.get(node["node"], {}),
        ).model_dump(),
    )

    yield (
        "proxmox_ve_node_attributes",
        SectionNodeAttributes(
            cluster=node_cluster_mapping.get(node["node"], ""),
            node_name=node["node"],
        ).model_dump_json(),
    )

    yield "proxmox_ve_ha_manager_status", ha_manager_status.model_dump()
    if "mem" in node and "maxmem" in node:
        yield (
            "proxmox_ve_mem_usage",
            {
                "mem": node["mem"],
                "max_mem": node["maxmem"],
            },
        )


def _create_vm_sections(
    vmid: str,
    vm: Any,
    config_lock_data: Mapping[str, Mapping[str, str]],
    logged_backup_data: Mapping[str, object],
    snapshot_data: Mapping[str, object],
    node_cluster_mapping: Mapping[str, object],
) -> Iterable[tuple[str, object]]:
    lock_str = config_lock_data.get(vmid, {}).get("lock")
    lock_state = LockState(lock_str) if lock_str else None
    yield (
        "proxmox_ve_vm_info",
        SectionVMInfo(
            vmid=vmid,
            node=vm["node"],
            type=vm["type"],
            status=vm["status"],
            name=vm["name"],
            uptime=vm["uptime"],
            lock=lock_state,
            cluster=str(node_cluster_mapping[vm["node"]])
            if vm["node"] in node_cluster_mapping
            else None,
        ).model_dump(mode="json"),
    )
    if vm["type"] != "qemu":
        yield (
            "proxmox_ve_disk_usage",
            {
                "disk": vm["disk"],
                "max_disk": vm["maxdisk"],
            },
        )
    yield (
        "proxmox_ve_disk_throughput",
        {
            "disk_read": vm["diskread"],
            "disk_write": vm["diskwrite"],
            "uptime": vm["uptime"],
        },
    )
    yield (
        "proxmox_ve_mem_usage",
        {
            "mem": vm["mem"],
            "max_mem": vm["maxmem"],
        },
    )
    yield (
        "proxmox_ve_network_throughput",
        {
            "net_in": vm["netin"],
            "net_out": vm["netout"],
            "uptime": vm["uptime"],
        },
    )
    yield (
        "proxmox_ve_cpu_util",
        {
            "cpu": vm["cpu"],
            "max_cpu": vm["maxcpu"],
            "uptime": vm["uptime"],
        },
    )
    yield (
        "proxmox_ve_vm_backup_status",
        {
            # todo: info about erroneous backups
            "last_backup": logged_backup_data.get(vmid),
        },
    )
    yield ("proxmox_ve_vm_snapshot_age", snapshot_data.get(vmid))


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    """Main entry point to be used"""
    try:
        return agent_proxmox_ve_main(parse_arguments(sys.argv[1:]))
    except CannotRecover as e:
        sys.stderr.write(f"{e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
