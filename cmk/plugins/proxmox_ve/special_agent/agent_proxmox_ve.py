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
import re
import sys
from collections.abc import Collection, Iterable, Mapping, MutableMapping, Sequence
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Any
from zoneinfo import ZoneInfo

import requests

from cmk.utils.paths import tmp_dir

from cmk.special_agents.v0_unstable.agent_common import (
    CannotRecover,
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.misc import JsonCachedData, to_bytes

LOGGER = logging.getLogger("agent_proxmox_ve")

RequestStructure = Sequence[Mapping[str, Any]] | Mapping[str, Any]
TaskInfo = Mapping[str, Any]
BackupInfo = MutableMapping[str, Any]
LogData = Iterable[Mapping[str, Any]]  # [{"d": int, "t": str}, {}, ..]

LogCacheFilePath = tmp_dir / "special_agents" / "agent_proxmox_ve"


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


class BackupTask:
    """Handles a bunch of log lines and turns them into a set of data needed from the log"""

    class LogParseError(RuntimeError):
        def __init__(self, line: int, msg: str) -> None:
            super().__init__(msg)
            self.line = line

        def __repr__(self) -> str:
            return "%s(%d, %r)" % (self.__class__.__name__, self.line, super().__str__())

    class LogParseWarning(LogParseError):
        """Less critical version of LogParseError"""

    def __init__(
        self,
        task: TaskInfo,
        logs: LogData,
        strict: bool,
        dump_logs: bool = False,
        dump_erroneous_logs: bool = True,
    ) -> None:
        self.upid, self.type, self.starttime, self.status = "", "", 0, ""
        self.__dict__.update(task)

        if dump_logs:
            with (LogCacheFilePath / (f"{task['upid']}.log")).open("w") as file:
                LOGGER.debug("wrote log to: %s", file.name)
                file.write("\n".join(line["t"] for line in logs))

        try:
            self.backup_data, errors = self._extract_logs(self._to_lines(logs), strict)
        except self.LogParseError as exc:
            # Note: this way of error handling is not ideal. In case a log file could not be
            #       parsed, all gathered data will be ignored and a error message get's written
            #       to the console.
            #       Crashing on the other hand is also bad since we don't have a way to gracefully
            #       handle unknown log file formats.
            #       An option would be to write error data to each VM being mentioned by the
            #       backup.
            #       I don't handle this issue in this change because further communication is
            #       needed and improving testability is still worth it.
            if strict:
                raise
            self.backup_data, errors = {}, [(exc.line, str(exc))]

        if errors and dump_erroneous_logs:
            with (LogCacheFilePath / (f"erroneous-{task['upid']}.log")).open("w") as file:
                LOGGER.error(
                    "Parsing the log for UPID=%r resulted in a error(s) - write log content to %r",
                    task["upid"],
                    file.name,
                )
                file.write("\n".join(line["t"] for line in logs))
                for linenr, text in errors:
                    file.write("PARSE-ERROR: %d: %s\n" % (linenr, text))

    @staticmethod
    def _to_lines(lines_with_numbers: LogData) -> Iterable[str]:
        """Extract line data from list of dicts containing redundant line numbers and line data
        >>> list(BackupTask._to_lines([{"n": 1, "t": "line1"}, {"n": 2, "t": "line2"}]))
        ['line1', 'line2']
        """
        # this has been true all the time and is left here for documentation
        # assert all((int(elem["n"]) - 1 == i) for i, elem in enumerate(lines_with_numbers))
        return (
            line
            for elem in lines_with_numbers
            for line in (elem["t"],)
            if isinstance(line, str) and line.strip()
        )

    def __str__(self) -> str:
        return "BackupTask({!r}, t={!r}, vms={!r})".format(
            self.type,
            datetime.fromtimestamp(self.starttime).strftime("%Y.%m.%d-%H:%M:%S"),
            tuple(self.backup_data.keys()),
        )

    @staticmethod
    def _extract_logs(
        logs: Iterable[str],
        strict: bool,
    ) -> tuple[Mapping[str, BackupInfo], Collection[tuple[int, str]]]:
        log_line_pattern = {
            key: re.compile(pat, flags=re.IGNORECASE)
            for key, pat in (
                # not yet used - might be interesting for consistency
                # (
                #     "start_job",
                #     r"^INFO: starting new backup job: vzdump (.*)",
                # ),
                # those for pattern must exist for every VM
                (
                    "start_vm",
                    r"^INFO: Starting Backup of VM (\d+).*",
                ),
                (
                    "started_time",
                    r"^INFO: Backup started at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
                ),
                (
                    "finish_vm",
                    r"^INFO: Finished Backup of VM (\d+) \((\d{2}:\d{2}:\d{2})\).*",
                ),
                (
                    "error_vm",
                    r"^ERROR: Backup of VM (\d+) failed - (.*)$",
                ),
                (
                    "failed_job",
                    r"^INFO: Failed at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$",
                ),
                (
                    "create_archive",
                    r"^INFO: creating(?: vzdump)? archive '(.*)'",
                ),
                (
                    "bytes_written",
                    r"^INFO: Total bytes written: (\d+) \(.*, (.*)\/s\)",
                ),
                (
                    "transferred",
                    r"^INFO: transferred (.*) in <?(\d+) seconds(.*)$",
                ),
                (
                    "uploaded",
                    r"^INFO: (.*): had to upload (.*) of (.*) in (.*)s, average speed (.*)/s",
                ),
                (
                    "archive_size",
                    r"^INFO: archive file size: (.*)",
                ),
                (
                    "backuped",
                    r"^INFO: (.*): had to backup (.*) of (.*) \(compressed (.*)\) in ([\d.]+)[\s]*s.*",
                ),
            )
        }
        required_keys = (
            {"started_time", "total_duration", "bytes_written_bandwidth", "bytes_written_size"},
            {"started_time", "total_duration", "transfer_size", "transfer_time"},
            {"started_time", "total_duration", "upload_amount", "upload_time", "upload_total"},
            {"started_time", "total_duration", "backup_amount", "backup_time", "backup_total"},
            {"started_time", "total_duration", "archive_name", "archive_size"},
        )

        result: dict[str, dict[str, Any]] = {}  # mutable Mapping[str, Mapping[str, Any]]
        current_vmid = ""
        current_dataset: dict[str, Any] = {}  # mutable Mapping[str, Any]
        errors = []

        def extract_tuple(line: str, pattern_name: str, count: int = 1) -> Sequence[str] | None:
            if match := log_line_pattern[pattern_name].match(line):
                return match.groups()[:count]
            return None

        def extract_single_value(line: str, pattern_name: str) -> str | None:
            if match := extract_tuple(line, pattern_name, 1):
                return match[0]
            return None

        def duration_from_string(string: str) -> float:
            """Return number of seconds from a string like HH:MM:SS
            >>> duration_from_string("21:43:44")
            78224.0
            >>> duration_from_string("44:00:44")
            158444.0
            """
            h, m, s = (int(x) for x in string.split(":"))
            return timedelta(hours=h, minutes=m, seconds=s).total_seconds()

        for linenr, line in enumerate(logs):
            try:
                if start_vmid := extract_single_value(line, "start_vm"):
                    if current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            f"Captured start of rocessing VM {start_vmid!r} while VM {current_vmid!r} is still active",
                        )
                    current_vmid = start_vmid
                    current_dataset = {}

                elif finish_vm := extract_tuple(line, "finish_vm", 2):
                    stop_vmid, duration_str = finish_vm
                    if stop_vmid != current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            f"Found end of VM {stop_vmid!r} while another VM {current_vmid!r} was active",
                        )
                    current_dataset["total_duration"] = duration_from_string(duration_str)

                    # complain if there are missing keys for any satisfying combination of keys
                    if all(r - set(current_dataset.keys()) for r in required_keys):
                        raise BackupTask.LogParseWarning(
                            linenr,
                            f"End of VM {current_vmid!r} while still information is missing (we have: {set(current_dataset.keys())!r})",
                        )
                    result[current_vmid] = current_dataset
                    current_vmid = ""

                elif error_vm := extract_tuple(line, "error_vm", 2):
                    error_vmid, error_msg = error_vm
                    if current_vmid and error_vmid != current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            f"Error for VM {error_vmid!r} while another VM {current_vmid!r} was active",
                        )
                    LOGGER.warning("Found error for VM %r: %r", error_vmid, error_msg)
                    result[error_vmid] = {**current_dataset, **{"error": error_msg}}
                    current_vmid = ""

                elif started_time := extract_single_value(line, "started_time"):
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr,
                            "Found start date while no VM was active",
                        )
                    current_dataset["started_time"] = started_time

                elif failed_at_time := extract_single_value(line, "failed_job"):
                    # in case a backup job fails we store the time it failed as
                    # 'started_time' in order to be able to sort backup jobs
                    for backup_data in result.values():
                        backup_data.setdefault("started_time", failed_at_time)

                elif bytes_written := extract_tuple(line, "bytes_written", 2):
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found bandwidth information while no VM was active"
                        )
                    current_dataset["bytes_written_size"] = int(bytes_written[0])
                    current_dataset["bytes_written_bandwidth"] = to_bytes(bytes_written[1])

                elif transferred := extract_tuple(line, "transferred", 2):
                    transfer_size, transfer_time = transferred
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found bandwidth information while no VM was active"
                        )
                    current_dataset["transfer_size"] = to_bytes(transfer_size)
                    current_dataset["transfer_time"] = int(transfer_time)

                elif archive_name := extract_single_value(line, "create_archive"):
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr,
                            "Found archive name without active VM",
                        )
                    current_dataset["archive_name"] = archive_name

                elif archive_size := extract_single_value(line, "archive_size"):
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found archive size information without active VM"
                        )
                    current_dataset["archive_size"] = to_bytes(archive_size)

                elif uploaded := extract_tuple(line, "uploaded", 5):
                    _, upload_amount, upload_total, upload_time, _ = uploaded
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found upload information while no VM was active"
                        )
                    current_dataset["upload_amount"] = to_bytes(upload_amount)
                    current_dataset["upload_total"] = to_bytes(upload_total)
                    current_dataset["upload_time"] = float(upload_time)

                elif backuped := extract_tuple(line, "backuped", 5):
                    _, backup_amount, backup_total, _, backup_time = backuped
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found backup information while no VM was active"
                        )
                    current_dataset["backup_amount"] = to_bytes(backup_amount)
                    current_dataset["backup_total"] = to_bytes(backup_total)
                    current_dataset["backup_time"] = float(backup_time)

            except BackupTask.LogParseWarning as exc:
                if strict:
                    raise
                logging.error("Error in log at line %d: %r", linenr, exc)
                current_vmid, current_dataset = "", {}
                errors.append((linenr, str(exc)))

        if current_vmid:
            errors.append((0, "Log for VMID=%r not finalized" % current_vmid))

        return result, errors


def collect_vm_backup_info(backup_tasks: Iterable[BackupTask]) -> Mapping[str, BackupInfo]:
    backup_data: dict[str, BackupInfo] = {}
    for task in backup_tasks:
        LOGGER.info("%s", task)
        LOGGER.debug("%r", task.backup_data)
        # Look for the latest backup for a given VMID in all backup task logs.
        for vmid, bdata in task.backup_data.items():
            # skip if we have a already newer backup
            if vmid in backup_data and backup_data[vmid]["started_time"] > bdata["started_time"]:
                continue
            backup_data[vmid] = bdata
    return backup_data


def fetch_backup_data(
    args: Args,
    session: "ProxmoxVeAPI",
    nodes: Iterable[Mapping[str, Any]],
) -> Mapping[str, BackupInfo]:
    """Since the Proxmox API does not provide us with information about past backups we read the
    information we need from log entries created for each backup process"""
    # Fetching log files is by far the most time consuming process issued by the ProxmoxVE agent.
    # Since logs have a unique UPID we can safely cache them
    cutoff_date = int((datetime.now() - timedelta(weeks=args.log_cutoff_weeks)).timestamp())
    with JsonCachedData(
        LogCacheFilePath / args.hostname / "upid.log.cache.json",
        cutoff_condition=lambda k, v: bool(v[0] < cutoff_date),
    ) as cached:

        def fetch_backup_log(task: TaskInfo, node: str) -> tuple[str, LogData]:
            """Make a call to session.get_tree() to get a log only if it's not cached
            Note: this is just a closure to make the call below less complicated - it could
            also be part of the generator"""
            # todo: specify type, date in request
            timestamp, logs = cached(
                task["upid"],
                lambda t=task, n=node: (
                    t["starttime"],
                    session.get_tree({"nodes": {n: {"tasks": {t["upid"]: {"log": []}}}}})["nodes"][
                        n
                    ]["tasks"][t["upid"]]["log"],
                ),
            )
            return timestamp, logs

        # todo: check vmid, typefilter source
        #       https://pve.proxmox.com/pve-docs/api-viewer/#/nodes/{node}/tasks
        return collect_vm_backup_info(
            BackupTask(task, backup_log, strict=args.debug, dump_logs=args.dump_logs)
            for node in nodes
            for task in node["tasks"]
            if (task["type"] == "vzdump" and int(task["starttime"]) >= cutoff_date)
            for _timestamp, backup_log in (fetch_backup_log(task, node["node"]),)
        )  #


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


class ProxmoxVeSession:
    """Session"""

    class HTTPAuth(requests.auth.AuthBase):
        """Auth"""

        def __init__(
            self,
            base_url: str,
            credentials: Mapping[str, str],
            timeout: int,
            verify_ssl: bool,
        ) -> None:
            super().__init__()
            ticket_url = base_url + "api2/json/access/ticket"
            response = (
                requests.post(url=ticket_url, verify=verify_ssl, data=credentials, timeout=timeout)
                .json()
                .get("data")
            )

            if response is None:
                raise CannotRecover(
                    "Couldn't authenticate {!r} @ {!r}".format(
                        credentials.get("username", "no-username"), ticket_url
                    )
                )

            self.pve_auth_cookie = response["ticket"]
            self.csrf_prevention_token = response["CSRFPreventionToken"]

        def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
            r.headers["CSRFPreventionToken"] = self.csrf_prevention_token
            return r

    def __init__(
        self,
        endpoint: tuple[str, int],
        credentials: Mapping[str, str],
        timeout: int,
        verify_ssl: bool,
    ) -> None:
        def create_session() -> requests.Session:
            session = requests.Session()
            session.auth = self.HTTPAuth(self._base_url, credentials, timeout, verify_ssl)
            session.cookies = requests.cookies.cookiejar_from_dict(
                {"PVEAuthCookie": session.auth.pve_auth_cookie}
            )
            session.headers["Connection"] = "keep-alive"
            session.headers["accept"] = ", ".join(
                (
                    "application/json",
                    "application/x-javascript",
                    "text/javascript",
                    "text/x-javascript",
                    "text/x-json",
                )
            )
            return session

        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._base_url = "https://%s:%d/" % endpoint
        self._session = create_session()

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """close connection to Proxmox VE endpoint"""
        self._session.close()

    def get_api_element(self, path: str) -> object:
        """do an API GET request"""
        try:
            return self._get_raw("api2/json/" + path)
        except requests.exceptions.ReadTimeout:
            raise CannotRecover(f"Read timeout after {self._timeout}s when trying to GET {path}")
        except requests.exceptions.ConnectionError as exc:
            raise CannotRecover(f"Could not GET element {path} ({exc})") from exc
        except JSONDecodeError as e:
            raise CannotRecover("Couldn't parse API element %r" % path) from e

    def _get_raw(self, sub_url: str) -> object:
        return (
            self._get_logs_or_tasks_paginated(sub_url)
            if (sub_url.endswith("/log") or sub_url.endswith("/tasks"))
            else self._validate_response(
                self._session.get(
                    url=self._base_url + sub_url,
                    verify=self._verify_ssl,
                    timeout=self._timeout,
                ),
                sub_url,
            )
        )

    def _get_logs_or_tasks_paginated(self, sub_url: str) -> list[object]:
        url = self._base_url + sub_url
        data: list[object] = []
        start = 0
        page_size = 5000

        while True:
            response_data = self._validate_response(
                self._session.get(
                    url=url,
                    verify=self._verify_ssl,
                    timeout=self._timeout,
                    params={"start": start, "limit": page_size},
                ),
                sub_url,
            )
            assert isinstance(response_data, Sequence)
            data += response_data

            if len(response_data) < page_size:
                break

            start += page_size

        return data

    @staticmethod
    def _validate_response(response: requests.Response, sub_url: str) -> object:
        if not response.ok:
            return []
        response_json = response.json()
        if "errors" in response_json:
            raise CannotRecover(
                "Could not fetch {!r} ({!r})".format(sub_url, response_json["errors"])
            )
        return response_json.get("data")


class ProxmoxVeAPI:
    """Wrapper for ProxmoxVeSession which provides high level API calls"""

    def __init__(
        self, host: str, port: int, credentials: Any, timeout: int, verify_ssl: bool
    ) -> None:
        try:
            LOGGER.info("Establish connection to Proxmox VE host %r", host)
            self._session = ProxmoxVeSession(
                endpoint=(host, port),
                credentials=credentials,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )
        except requests.exceptions.ConnectTimeout:
            raise CannotRecover(f"Timeout after {timeout}s when trying to connect to {host}:{port}")
        except requests.exceptions.ConnectionError as exc:
            raise CannotRecover(f"Could not connect to {host}:{port} ({exc})") from exc

    def __enter__(self) -> Any:
        self._session.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._session.__exit__(*exc_info)
        self._session.close()

    def get(self, path: str | Iterable[str]) -> Any:
        """Handle request items in form of 'path/to/item' or ['path', 'to', 'item']"""
        return self._session.get_api_element(
            path if isinstance(path, str) else "/".join(map(str, path))
        )

    def get_tree(self, requested_structure: RequestStructure) -> Any:
        def rec_get_tree(
            element_name: str | None,
            requested_structure: RequestStructure,
            path: Iterable[str],
        ) -> Any:
            """Recursively fetch data from API to match <requested_structure>"""

            def is_list_of_subtree_names(data: RequestStructure) -> bool:
                """Return True if given data is a list of dicts containing names of subtrees,
                e.g [{'name': 'log'}, {'name': 'options'}, ...]"""
                return bool(data) and all(
                    isinstance(elem, Mapping) and tuple(elem) in {("name",), ("subdir",), ("cmd",)}
                    for elem in data
                )

            def extract_request_subtree(request_tree: RequestStructure) -> RequestStructure:
                """If list if given return first (and only) element return the provided data tree"""
                return (
                    request_tree
                    if isinstance(request_tree, Mapping)
                    else next(iter(request_tree))
                    if len(request_tree) > 0
                    else {}
                )

            def extract_variable(st: RequestStructure) -> Mapping[str, Any] | None:
                """Check if there is exactly one root element with a variable name,
                e.g. '{node}' and return its stripped name"""
                if not isinstance(st, Mapping):
                    return None
                if len(st) != 1 or not next(iter(st)).startswith("{"):
                    # we have either exactly one variable or no variables at all
                    assert len(st) != 1 or all(not e.startswith("{") for e in st)
                    return None
                key, value = next(iter(st.items()))
                assert len(st) == 1 and key.startswith("{")
                return {"name": key.strip("{}"), "subtree": value}

            next_path = list(path) + ([] if element_name is None else [element_name])
            subtree = extract_request_subtree(requested_structure)
            variable = extract_variable(subtree)
            response = self._session.get_api_element("/".join(map(str, next_path)))

            if isinstance(response, Sequence):
                # Handle subtree stubs like [{'name': 'log'}, {'name': 'options'}, ...]
                if is_list_of_subtree_names(response):
                    assert variable is None
                    assert not isinstance(requested_structure, Sequence) and isinstance(
                        subtree, Mapping
                    )
                    assert subtree
                    subdir_names = (
                        (
                            elem[
                                next(
                                    identifier
                                    for identifier in ("name", "subdir", "cmd")
                                    if identifier in elem
                                )
                            ]
                        )
                        for elem in response
                    )
                    return {
                        key: rec_get_tree(key, subtree[key], next_path)
                        for key in subdir_names
                        if key in subtree
                    }

                # Handle case when response is a list of arbitrary datasets
                #  e.g [{'uptime': 12345}, 'id': 'server-1', ...}, ...]"""
                if all(isinstance(elem, Mapping) for elem in response):
                    if variable is None:
                        assert isinstance(subtree, Mapping)
                        return (
                            {key: rec_get_tree(key, subtree[key], next_path) for key in subtree}
                            if isinstance(requested_structure, Mapping)
                            else response
                        )  #

                    assert isinstance(requested_structure, Sequence)
                    return [
                        {
                            **elem,
                            **(
                                rec_get_tree(
                                    elem[variable["name"]],
                                    variable["subtree"],
                                    next_path,
                                )
                                or {}
                            ),
                        }
                        for elem in response
                    ]

            return response

        return rec_get_tree(None, requested_structure, [])


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_proxmox_ve_main)


if __name__ == "__main__":
    sys.exit(main())
