#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Checkmk Proxmox VE special agent, currently reporting the following
information about VMs and nodes:
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

import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from cmk.plugins.proxmox_ve.special_agent.libbackups import fetch_backup_data
from cmk.plugins.proxmox_ve.special_agent.libproxmox import ProxmoxVeAPI
from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

LOGGER = logging.getLogger("agent_proxmox_ve")


def parse_arguments(argv: Sequence[str] | None) -> Args:
    """parse command line arguments and return argument object"""
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--timeout", "-t", type=int, default=50, help="API call timeout")
    parser.add_argument("--port", type=int, default=8006, help="IPv4 port to connect to")
    parser.add_argument("--username", "-u", type=str, help="username for connection")
    parser.add_argument("--password", "-p", type=str, help="password for connection")
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


def agent_proxmox_ve_main(args: Args) -> int:
    """Fetches and writes selected information formatted as agent output to stdout"""
    with ProxmoxVeAPI(
        host=args.hostname,
        port=args.port,
        credentials={k: getattr(args, k) for k in ("username", "password") if getattr(args, k)},
        timeout=args.timeout,
        verify_ssl=not args.no_cert_check,
    ) as session:
        LOGGER.info("Fetch general cluster and node information..")
        data = session.get_tree(
            {
                "cluster": {
                    "backup": [],
                    "resources": [],
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
                                    }
                                }
                            ],
                            "lxc": [
                                {
                                    "{vmid}": {
                                        "snapshot": [],
                                    }
                                }
                            ],
                            "version": {},
                            "time": {},
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

    for node in data["nodes"]:
        if (timezone := node["time"].get("timezone")) is not None:
            node_timezones[node["node"]] = timezone
        # only lxc and qemu can have snapshots
        for vm in node.get("lxc", []) + node.get("qemu", []):
            snapshot_data[str(vm["vmid"])] = {
                "snaptimes": [x["snaptime"] for x in vm["snapshot"] if "snaptime" in x],
            }

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
        piggyback_host = None if args.hostname.startswith(node["node"] + ".") else node["node"]
        with ConditionalPiggybackSection(piggyback_host):
            with SectionWriter("proxmox_ve_node_info") as writer:
                writer.append_json(
                    {
                        "status": node["status"],
                        "lxc": [vmid for vmid in all_vms if all_vms[vmid]["type"] == "lxc"],
                        "qemu": [vmid for vmid in all_vms if all_vms[vmid]["type"] == "qemu"],
                        "proxmox_ve_version": node["version"],
                        "time_info": node["time"],
                        "subscription": {
                            key: value
                            for key, value in node["subscription"].items()
                            if key
                            in {
                                "status",
                                "checktime",
                                "key",
                                "level",
                                "nextduedate",
                                "productname",
                                "regdate",
                            }
                        },
                    }
                )
            if "mem" in node and "maxmem" in node:
                with SectionWriter("proxmox_ve_mem_usage") as writer:
                    writer.append_json(
                        {
                            "mem": node["mem"],
                            "max_mem": node["maxmem"],
                        }
                    )
            if "uptime" in node:
                with SectionWriter("uptime", separator=None) as writer:
                    writer.append(node["uptime"])

    for vmid, vm in all_vms.items():
        with ConditionalPiggybackSection(vm["name"]):
            with SectionWriter("proxmox_ve_vm_info") as writer:
                writer.append_json(
                    {
                        "vmid": vmid,
                        "node": vm["node"],
                        "type": vm["type"],
                        "status": vm["status"],
                        "name": vm["name"],
                        "uptime": vm["uptime"],
                    }
                )
            if vm["type"] != "qemu":
                with SectionWriter("proxmox_ve_disk_usage") as writer:
                    writer.append_json(
                        {
                            "disk": vm["disk"],
                            "max_disk": vm["maxdisk"],
                        }
                    )
            with SectionWriter("proxmox_ve_disk_throughput") as writer:
                writer.append_json(
                    {
                        "disk_read": vm["diskread"],
                        "disk_write": vm["diskwrite"],
                        "uptime": vm["uptime"],
                    }
                )
            with SectionWriter("proxmox_ve_mem_usage") as writer:
                writer.append_json(
                    {
                        "mem": vm["mem"],
                        "max_mem": vm["maxmem"],
                    }
                )
            with SectionWriter("proxmox_ve_network_throughput") as writer:
                writer.append_json(
                    {
                        "net_in": vm["netin"],
                        "net_out": vm["netout"],
                        "uptime": vm["uptime"],
                    }
                )
            with SectionWriter("proxmox_ve_cpu_util") as writer:
                writer.append_json(
                    {
                        "cpu": vm["cpu"],
                        "max_cpu": vm["maxcpu"],
                        "uptime": vm["uptime"],
                    }
                )
            with SectionWriter("proxmox_ve_vm_backup_status") as writer:
                writer.append_json(
                    {
                        # todo: info about erroneous backups
                        "last_backup": logged_backup_data.get(vmid),
                    }
                )
            with SectionWriter("proxmox_ve_vm_snapshot_age") as writer:
                writer.append_json(snapshot_data.get(vmid))

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_proxmox_ve_main)


if __name__ == "__main__":
    sys.exit(main())
