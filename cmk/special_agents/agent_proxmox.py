#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Checkmk Proxmox special agent

Domain    | Element                       | Check
----------+-------------------------------+---------------------------------------------------------
Proxmox   |                               |
          | Proxmox Version               | --- checked for each node
          | Configured, Backup            | --- checked for each vm proxmox_cluster_backup_status
          | log-cutoff-weeks              |
          |                               |
----------+-------------------------------+---------------------------------------------------------
Nodes []  |                               |
          | Proxmox Version               | proxmox_node_info
          | Subscription                  | proxmox_node_info
          | Status: "active"/"inactive"   | proxmox_node_info
          | lxc: []                       | proxmox_node_info
          | qemu: []                      | proxmox_node_info
          |                               |
          | Uptime                        | uptime (existing)
          |                               |
          | disk usage   (%/max)          | proxmox_disk_usage
          | mem usage    (%/max)          | proxmox_mem_usage
          |                               |
          | # backup                      | todo: summary status for VMs configured on this node
          | # snapshots                   | todo: summary status for VMs configured on this node
          | # replication                 | ---
          |                               |
----------+-------------------------------+---------------------------------------------------------
VMs []    |                               |
          | vmid: int                     | proxmox_vm_info
          | type: lxc/qemu                | proxmox_vm_info
          | node: host                    | proxmox_vm_info (vllt. konfigurierbare überprüfung?)
          | status: running/not running   | proxmox_vm_info
          |                               |
          | disk usage                    | [x] proxmox_disk_usage / only lxc
          | mem usage                     | [x] proxmox_mem_usage

          | Backed up                     | [x] proxmox_vm_backup_status
          |     When / crit / warn        | [x]
          |     Failure as warning        | [x]
          |     Bandwidth                 | [?]
          |                               |
          | # replication                 | todo: ähnlich wie backup
          | # snapshots                   | todo: warn about snapshots > 1 day / more than N
          |                               |
----------+-------------------------------+---------------------------------------------------------
"""

# Todo:
# - Replication Status VMs & Container, Gesamtstatus + piggybacked

# Read:
# - https://pve.proxmox.com/wiki/Proxmox_VE_API
# - https://pve.proxmox.com/pve-docs/api-viewer/
# - https://pve.proxmox.com/pve-docs/api-viewer/apidoc.js
# - https://pypi.org/project/proxmoxer/

import sys
import json
import argparse
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Any, List, Dict, Union, Optional, Tuple, Sequence, Generator

import requests
from requests.packages import urllib3

import cmk.utils.password_store
from cmk.utils.paths import tmp_dir

from cmk.special_agents.utils import vcrtrace

LOGGER = logging.getLogger("agent_proxmox")

ListOrDict = Union[List[Dict[str, Any]], Dict[str, Any]]
Args = argparse.Namespace
TaskInfo = Dict[str, Any]
BackupInfo = Dict[str, Any]
LogData = Sequence[Dict[str, Any]]  # [{"d": int, "t": str}, {}, ..]

LogCacheFilePath = Path(tmp_dir) / "special_agents" / "agent_proxmox"


def parse_arguments(argv: Sequence[str]) -> Args:
    """parse command line arguments and return argument object"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[("authorization", "****")]))
    parser.add_argument("--timeout", "-t", type=int, default=20, help="API call timeout")
    parser.add_argument("--port", type=int, default=8006, help="IPv4 port to connect to")
    parser.add_argument("--username", "-u", type=str, help="username for connection")
    parser.add_argument("--password", "-p", type=str, help="password for connection")
    parser.add_argument("--verbose", "-v", action="count", default=0)
    # TODO: warn if log-cutoff-weeks is shorter than actual log length or
    #       shorter than configured check
    parser.add_argument(
        "--log-cutoff-weeks",
        type=int,
        default=2,
        help="Fetch logs N weeks back in time",
    )
    parser.add_argument("--no-cert-check", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Keep some exceptions unhandled")
    parser.add_argument("hostname", help="Name of the Proxmox instance to query.")
    return parser.parse_args(argv)


class BackupTask:
    """Handles a bunch of log lines and turns them into a set of data needed from the log
    """
    class LogParseError(RuntimeError):
        def __init__(self, line: int, msg: str) -> None:
            super().__init__(msg)
            self.line = line

        def __repr__(self) -> str:
            return "%s(%d, %r)" % (self.__class__.__name__, self.line, super().__str__())

    class LogParseWarning(LogParseError):
        """Less critical version of LogParseError"""

    def __init__(self, task: TaskInfo, logs: LogData, strict: bool) -> None:
        self.upid, self.type, self.starttime, self.status = "", "", 0, ""
        self.__dict__.update(task)

        try:
            self.backup_data, errors = self._extract_logs(self._to_lines(logs), strict)
        except self.LogParseError as exc:
            self.backup_data, errors = {}, [(exc.line, str(exc))]

        if errors:
            erroneous_log_file = LogCacheFilePath / ("erroneous-%s.log" % task["upid"])
            LOGGER.error(
                "Parsing the log for UPID=%r resulted in a error(s) - "
                "write log content to %r", task["upid"], erroneous_log_file)
            with erroneous_log_file.open("w") as file:
                file.write("\n".join(line["t"] for line in logs))
                for linenr, text in errors:
                    file.write("PARSE-ERROR: %d: %s\n" % (linenr, text))

    @staticmethod
    def _to_lines(lines_with_numbers: LogData) -> Sequence[str]:
        """ Gets list of dict containing a line number an a line [{"n": int, "t": str}*]
        Returns List of lines only"""
        return tuple(  #
            line  #
            for elem in lines_with_numbers  #
            for line in (elem["t"],)  #
            if isinstance(line, str) and line.strip())

    def __str__(self) -> str:
        return "BackupTask(%r, t=%r, vms=%r)" % (
            self.type,
            datetime.fromtimestamp(self.starttime).strftime("%Y.%m.%d-%H:%M:%S"),
            tuple(self.backup_data.keys()),
        )

    @staticmethod
    def _extract_logs(
        logs: Sequence[str],
        strict: bool,
    ) -> Tuple[Dict[str, BackupInfo], List[Tuple[int, str]]]:
        log_line_pattern = {
            key: re.compile(pat, flags=re.IGNORECASE) for key, pat in (
                ("start_job", r"^INFO: starting new backup job: vzdump (.*)"),
                ("start_vm", r"^INFO: Starting Backup of VM (\d+).*"),
                ("started_time", r"^INFO: Backup started at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"),
                ("finish_vm", r"^INFO: Finished Backup of VM (\d+) \((\d{2}:\d{2}:\d{2})\).*"),
                ("error_vm", r"^ERROR: Backup of VM (\d+) failed - (.*)$"),
                ("create_archive", r"^INFO: creating(?: vzdump)? archive '(.*)'"),
                ("bytes_written", r"^INFO: Total bytes written: (\d+) \(.*, (.*)\/s\)"),
                ("transferred", r"^INFO: transferred (\d+) MB in (\d+) seconds \(.*\)"),
                ("archive_size", r"^INFO: archive file size: (.*)"),
            )
        }
        result: Dict[str, BackupInfo] = {}
        current_vmid = ""
        current_dataset: BackupInfo = {}
        errors = []

        def extract_tuple(line: str, pattern_name: str, count: int = 1) -> Optional[Sequence[str]]:
            # TODO: use assignment expressions as soon as YAPF supports them or is dead
            match = log_line_pattern[pattern_name].match(line)
            if match:
                return match.groups()[:count]
            return None

        def extract_single_value(line: str, pattern_name: str) -> Optional[str]:
            # TODO: use assignment expressions as soon as YAPF supports them or is dead
            match = extract_tuple(line, pattern_name, 1)
            if match:
                return match[0]
            return None

        for linenr, line in enumerate(logs):
            try:
                # TODO: use assignment expressions together with elif and w/o continue
                start_vmid = extract_single_value(line, "start_vm")
                if start_vmid:
                    if current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            "Captured start of rocessing VM %r while VM %r is still active" %
                            (start_vmid, current_vmid),
                        )
                    current_vmid = start_vmid
                    current_dataset = {}
                    continue

                finish_vm = extract_tuple(line, "finish_vm", 2)
                if finish_vm:
                    stop_vmid, duration_str = finish_vm
                    if stop_vmid != current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            "Found end of VM %r while another VM %r was active" %
                            (stop_vmid, current_vmid),
                        )
                    if "transfer_time" not in current_dataset:
                        duration_dt = datetime.strptime(duration_str, "%H:%M:%S")
                        current_dataset["transfer_time"] = (duration_dt.hour * 3600 +
                                                            duration_dt.minute * 60 +
                                                            duration_dt.second)
                    missing_keys = {
                        key for key in
                        {"transfer_time", "archive_name", "archive_size", "started_time"}
                        if key not in current_dataset
                    }
                    if missing_keys:
                        raise BackupTask.LogParseWarning(
                            linenr,
                            "End of VM %r while still information is missing (missing: %r)" %
                            (current_vmid, missing_keys),
                        )
                    result[current_vmid] = current_dataset
                    current_vmid = ""
                    continue

                error_vm = extract_tuple(line, "error_vm", 2)
                if error_vm:
                    error_vmid, error_msg = error_vm
                    if current_vmid and error_vmid != current_vmid:
                        # this is a consistency problem - we have to abort parsing this log file
                        raise BackupTask.LogParseError(
                            linenr,
                            "Error for VM %r while another VM %r was active" %
                            (error_vmid, current_vmid),
                        )
                    LOGGER.warning("Found error for VM %r: %r", error_vmid, error_msg)
                    result[current_vmid] = {"error": error_msg}
                    current_vmid = ""
                    continue

                started_time = extract_single_value(line, "started_time")
                if started_time:
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr,
                            "Found start date while no VM was active",
                        )
                    current_dataset["started_time"] = started_time
                    continue

                bytes_written = extract_tuple(line, "bytes_written", 2)
                if bytes_written:
                    vm_size = int(bytes_written[0])
                    bandw = to_bytes(bytes_written[1])
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found bandwidth information while no VM was active")
                    current_dataset["transfer_size"] = vm_size
                    current_dataset["transfer_time"] = round(vm_size / bandw) if bandw > 0 else 0
                    continue

                transferred = extract_tuple(line, "transferred", 2)
                if transferred:
                    transfer_size_mb, transfer_time = transferred
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found bandwidth information while no VM was active")
                    current_dataset["transfer_size"] = int(transfer_size_mb) * (1 << 20)
                    current_dataset["transfer_time"] = int(transfer_time)
                    continue

                archive_name = extract_single_value(line, "create_archive")
                if archive_name:
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr,
                            "Found archive name without active VM",
                        )
                    current_dataset["archive_name"] = archive_name
                    continue

                archive_size = extract_single_value(line, "archive_size")
                if archive_size:
                    if not current_vmid:
                        raise BackupTask.LogParseWarning(
                            linenr, "Found archive size information without active VM")
                    current_dataset["archive_size"] = to_bytes(archive_size)
                    continue

            except BackupTask.LogParseWarning as exc:
                if strict:
                    raise
                logging.error("Error in log at line %d: %r", linenr, exc)
                current_vmid, current_dataset = "", {}
                errors.append((linenr, str(exc)))

        if current_vmid:
            errors.append((0, "Log for VMID=%r not finalized" % current_vmid))

        return result, errors


@contextmanager
def JsonCachedData(filename: str) -> Generator[Dict[str, Any], None, None]:
    """Store JSON-serializable data on filesystem and provide it if available"""
    LogCacheFilePath.mkdir(parents=True, exist_ok=True)
    cache_file = LogCacheFilePath / filename
    try:
        with cache_file.open() as crfile:
            cache = json.load(crfile)
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    try:
        yield cache
    finally:
        LOGGER.info("Write cache file: %r", str(cache_file.absolute()))
        with cache_file.open(mode="w") as cwfile:
            json.dump(cache, cwfile)


def fetch_backup_data(args: Args, session: "ProxmoxAPI",
                      nodes: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Since the Proxmox API does not provide us with information about past backups we read the
    information we need from log entries created for each backup process"""
    # Fetching log files is by far the most time consuming process issued by the Proxmox agent.
    # Since logs have a unique UPID we can safely cache them
    with JsonCachedData("upid.log.cache.json") as cache:
        cutoff_date = int((datetime.now() - timedelta(weeks=args.log_cutoff_weeks)).timestamp())
        # throw away older logs
        for upid in tuple((key for key, (date, _) in cache.items() if date < cutoff_date)):
            LOGGER.debug("erase log cache for %r", upid)
            del cache[upid]

        # todo: check vmid, typefilter source
        #       https://pve.proxmox.com/pve-docs/api-viewer/#/nodes/{node}/tasks
        backup_tasks = (
            BackupTask(
                task,
                cache[task["upid"]][1] if task["upid"] in cache else cache.setdefault(
                    task["upid"],
                    (
                        task["starttime"],
                        session.get_tree({
                            "nodes": {
                                node["node"]: {
                                    "tasks": {
                                        task["upid"]: {
                                            "log": [
                                                # todo: specify type, date in request
                                            ]
                                        }
                                    }
                                }
                            }
                        })["nodes"][node["node"]]["tasks"][task["upid"]]["log"]))[1],
                strict=args.debug)
            for node in nodes
            for task in node["tasks"]
            if (task["type"] == "vzdump" and int(task["starttime"]) >= cutoff_date))

        backup_data: Dict[str, BackupInfo] = {}
        for task in backup_tasks:
            LOGGER.info("%s", task)
            LOGGER.debug("%r", task.backup_data)
            for vmid, bdata in task.backup_data.items():
                if vmid in backup_data:
                    continue
                backup_data[vmid] = bdata

        return backup_data


def to_bytes(string: str) -> int:
    """Turn a string containing a byte-size with units like (MiB, ..) into an int
    containing the size in bytes

    >>> to_bytes("123")
    123
    >>> to_bytes("123KiB")
    125952
    >>> to_bytes("123 KiB")
    125952
    >>> to_bytes("123KB")
    125952
    >>> to_bytes("123 MiB")
    128974848
    >>> to_bytes("123 GiB")
    132070244352
    >>> to_bytes("123.5 GiB")
    132607115264
    """
    return round(  #
        (float(string[:-3]) * (1 << 10)) if string.endswith("KiB") else
        (float(string[:-2]) * (1 << 10)) if string.endswith("KB") else
        (float(string[:-3]) * (1 << 20)) if string.endswith("MiB") else
        (float(string[:-2]) * (1 << 20)) if string.endswith("MB") else
        (float(string[:-3]) * (1 << 30)) if string.endswith("GiB") else
        (float(string[:-2]) * (1 << 30)) if string.endswith("GB") else  #
        float(string))


def write_agent_output(args: argparse.Namespace) -> None:
    """Fetches and writes selected information formatted as agent output to stdout"""
    def write_piggyback_sections(host: str, sections: Sequence[Dict[str, Any]]) -> None:
        print("<<<<%s>>>>" % host)
        write_sections(sections)
        print("<<<<>>>>")

    def write_sections(sections: Sequence[Dict[str, Any]]) -> None:
        def write_section(name: str, data: Any, skip: bool = False, jsonify: bool = True) -> None:
            if skip:
                return
            print(("<<<%s:sep(0)>>>" if jsonify else "<<<%s>>>") % name)
            print(json.dumps(data, sort_keys=True) if jsonify else data)

        for section in sections:
            write_section(**section)

    with ProxmoxAPI(
            host=args.hostname,
            port=args.port,
            credentials={k: getattr(args, k) for k in {"username", "password"} if getattr(args, k)},
            timeout=args.timeout,
            verify_ssl=not args.no_cert_check,
    ) as session:
        LOGGER.info("Fetch general cluster and node information..")
        data = session.get_tree({
            "cluster": {
                "backup": [],
                "resources": [],
            },
            "nodes": [{
                "{node}": {
                    "subscription": {},
                    # for now just get basic task data - we'll read the logs later
                    "tasks": [],
                    "version": {},
                },
            }],
            "version": {},
        })

        LOGGER.info("Fetch and process backup logs..")
        logged_backup_data = fetch_backup_data(args, session, data["nodes"])

    all_vms = {
        str(entry["vmid"]): entry
        for entry in data["cluster"]["resources"]
        if entry["type"] in ("lxc", "qemu")
    }

    backup_data = {
        # generate list of all VMs IDs - both lxc and qemu
        "vmids": sorted(list(all_vms.keys())),
        # look up scheduled backups and extract assigned VMIDs
        "scheduled_vmids": sorted(
            list(
                set(vmid  #
                    for backup in data["cluster"]["backup"]
                    if "vmid" in backup and backup["enabled"] == "1"
                    for vmid in backup["vmid"].split(",")))),
        # add data of actually logged VMs
        "logged_vmids": logged_backup_data,
    }

    LOGGER.info("all VMs:          %r", backup_data["vmids"])
    LOGGER.info("expected backups: %r", backup_data["scheduled_vmids"])
    LOGGER.info("actual backups:   %r", sorted(list(logged_backup_data.keys())))

    LOGGER.info("Write agent output..")
    for node in data["nodes"]:
        assert node["type"] == "node"
        write_piggyback_sections(
            host=node["node"],
            sections=[
                {
                    "name": "proxmox_node_info",
                    "data": {
                        "status": node["status"],
                        "lxc": [vmid for vmid in all_vms if all_vms[vmid]["type"] == "lxc"],
                        "qemu": [vmid for vmid in all_vms if all_vms[vmid]["type"] == "qemu"],
                        "proxmox_version": node["version"],
                        "subscription": {
                            key: value for key, value in node["subscription"].items() if key in {
                                "status",
                                "checktime",
                                "key",
                                "level",
                                "nextduedate",
                                "productname",
                                "regdate",
                            }
                        },
                    },
                },
                {
                    "name": "proxmox_disk_usage",
                    "data": {
                        "disk": node["disk"],
                        "max_disk": node["maxdisk"],
                    },
                },
                {
                    "name": "proxmox_mem_usage",
                    "data": {
                        "mem": node["mem"],
                        "max_mem": node["maxmem"],
                    },
                },
                {
                    "name": "uptime",
                    "data": node["uptime"],
                    # don't write json since we use generic check plugin
                    "jsonify": False,
                },
                # {  # Todo
                #     "name": "proxmox_backup_summary",
                # },
                # {  # Todo
                #     "name": "proxmox_snapshot_summary",
                # },
            ],
        )

    for vmid, vm in all_vms.items():
        write_piggyback_sections(
            host=vm["name"],
            sections=[
                {
                    "name": "proxmox_vm_info",
                    "data": {
                        "vmid": vmid,
                        "node": vm["node"],
                        "type": vm["type"],
                        "status": vm["status"],
                        "name": vm["name"],
                    },
                },
                {
                    "name": "proxmox_disk_usage",
                    "data": {
                        "disk": vm["disk"],
                        "max_disk": vm["maxdisk"],
                    },
                    "skip": vm["type"] == "qemu",
                },
                {
                    "name": "proxmox_mem_usage",
                    "data": {
                        "mem": vm["mem"],
                        "max_mem": vm["maxmem"],
                    },
                },
                {
                    "name": "proxmox_vm_backup_status",
                    "data": {
                        # todo: info about erroneous backups
                        "last_backup": logged_backup_data.get(vmid),
                    },
                },
                # {  # Todo
                #     "name": "proxmox_vm_replication_status",
                # },
                # {  # Todo
                #     "name": "proxmox_vm_snapshot_status",
                # },
            ],
        )


class ProxmoxSession:
    """Session"""
    class HTTPAuth(requests.auth.AuthBase):
        """Auth"""
        def __init__(
            self,
            base_url: str,
            credentials: Dict[str, str],
            timeout: int,
            verify_ssl: bool,
        ) -> None:
            super(ProxmoxSession.HTTPAuth, self).__init__()
            ticket_url = base_url + "api2/json/access/ticket"
            response = (requests.post(url=ticket_url,
                                      verify=verify_ssl,
                                      data=credentials,
                                      timeout=timeout).json().get("data"))
            if response is None:
                raise RuntimeError("Couldn't authenticate %r @ %r" %
                                   (credentials.get("username", "no-username"), ticket_url))

            self.pve_auth_cookie = response["ticket"]
            self.csrf_prevention_token = response["CSRFPreventionToken"]

        def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
            r.headers["CSRFPreventionToken"] = self.csrf_prevention_token
            return r

    def __init__(
        self,
        endpoint: Tuple[str, int],
        credentials: Dict[str, str],
        timeout: int,
        verify_ssl: bool,
    ) -> None:
        def create_session() -> requests.Session:
            session = requests.Session()
            session.auth = self.HTTPAuth(self._base_url, credentials, timeout, verify_ssl)
            session.cookies = requests.cookies.cookiejar_from_dict(  # type: ignore
                {"PVEAuthCookie": session.auth.pve_auth_cookie})
            session.headers["Connection"] = "keep-alive"
            session.headers["accept"] = ", ".join((
                "application/json",
                "application/x-javascript",
                "text/javascript",
                "text/x-javascript",
                "text/x-json",
            ))
            return session

        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._base_url = "https://%s:%d/" % endpoint
        self._session = create_session()

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self.close()

    def close(self) -> None:
        """close connection to ProxMox endpoint"""
        if self._session:
            self._session.close()

    def get_raw(self, sub_url: str) -> requests.Response:
        return self._session.request(
            method="GET",
            url=self._base_url + sub_url,
            # todo: generic
            params={"limit": "5000"} if
            (sub_url.endswith("/log") or sub_url.endswith("/tasks")) else {},
            verify=self._verify_ssl,
            timeout=self._timeout,
        )

    def get_api_element(self, path: str) -> Any:
        """do an API GET request"""
        response_json = self.get_raw("api2/json/" + path).json()
        if "errors" in response_json:
            raise RuntimeError("Could not fetch %r (%r)" % (path, response_json["errors"]))
        return response_json.get("data")


class ProxmoxAPI:
    """Wrapper for ProxmoxSession which provides high level API calls"""
    def __init__(self, host: str, port: int, credentials: Any, timeout: int,
                 verify_ssl: bool) -> None:
        try:
            LOGGER.info("Establish connection to Proxmox host %r", host)
            self._session = ProxmoxSession(
                endpoint=(host, port),
                credentials=credentials,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )
        except requests.exceptions.ConnectTimeout as exc:
            # In order to make the exception traceback more readable truncate it to
            # this function - fallback to full stack on Python2
            raise exc.with_traceback(None) if hasattr(exc, "with_traceback") else exc

    def __enter__(self) -> Any:
        self._session.__enter__()
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self._session.__exit__(*args, **kwargs)
        self._session.close()

    def get(self, path: Union[str, List[str], Tuple[str]]) -> Any:
        """Handle request items in form of 'path/to/item' or ['path', 'to', 'item'] """
        return self._session.get_api_element("/".join(
            str(p) for p in path) if isinstance(path, (list, tuple)) else path)

    def get_tree(self, requested_structure: ListOrDict) -> Any:
        def rec_get_tree(
            element_name: Optional[str],
            requested_structure: ListOrDict,
            path: Sequence[str],
        ) -> Any:
            """Recursively fetch data from API to match <requested_structure>"""
            def is_list_of_subtree_names(data: ListOrDict) -> bool:
                """Return True if given data is a list of dicts containing names of subtrees,
                e.g [{'name': 'log'}, {'name': 'options'}, ...]"""
                return bool(data) and all(
                    isinstance(elem, dict) and tuple(elem) in {("name",), ("subdir",), ("cmd",)}
                    for elem in data)

            def extract_request_subtree(request_tree: ListOrDict) -> ListOrDict:
                """If list if given return first (and only) element return the provided data tree"""
                return (request_tree  #
                        if not isinstance(request_tree, list) else  #
                        next(iter(request_tree)) if len(request_tree) > 0 else  #
                        {})

            def extract_variable(st: ListOrDict) -> Optional[Dict[str, Any]]:
                """Check if there is exactly one root element with a variable name,
                e.g. '{node}' and return its stripped name"""
                if not isinstance(st, dict):
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
            response = self._session.get_api_element("/".join(next_path))

            if isinstance(response, list):
                # Handle subtree stubs like [{'name': 'log'}, {'name': 'options'}, ...]
                if is_list_of_subtree_names(response):
                    assert variable is None
                    assert not isinstance(requested_structure, list) and isinstance(subtree, dict)
                    assert subtree
                    subdir_names = ((elem[next(identifier
                                               for identifier in ("name", "subdir", "cmd")
                                               if identifier in elem)])
                                    for elem in response)
                    return {
                        key: rec_get_tree(key, subtree[key], next_path)
                        for key in subdir_names
                        if key in subtree
                    }

                # Handle case when response is a list of arbitrary datasets
                #  e.g [{'uptime': 12345}, 'id': 'server-1', ...}, ...]"""
                if all(isinstance(elem, dict) for elem in response):
                    if variable is None:
                        assert isinstance(subtree, dict)
                        return ({
                            key: rec_get_tree(key, subtree[key], next_path)  #
                            for key in subtree
                        } if isinstance(requested_structure, dict) else response)

                    assert isinstance(requested_structure, list)
                    return [{
                        **elem,
                        **(rec_get_tree(
                            elem[variable["name"]],
                            variable["subtree"],
                            next_path,
                        ) or {})
                    } for elem in response]

            return response

        return rec_get_tree(None, requested_structure, [])


def main(argv: Optional[Sequence[str]] = None) -> int:
    """read arguments, configure application and run command specified on command line"""
    if argv is None:
        cmk.utils.password_store.replace_passwords()
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # type: ignore
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level={
            0: logging.WARN,
            1: logging.INFO,
            2: logging.DEBUG
        }.get(args.verbose, logging.DEBUG),
    )
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("vcr").setLevel(logging.WARN)
    LOGGER.info("running file %s", __file__)
    LOGGER.info(
        "using Python interpreter v%s at %s",
        ".".join(str(e) for e in sys.version_info),
        sys.executable,
    )

    try:
        write_agent_output(args)
    except Exception as exc:
        if args.debug:
            raise
        sys.stderr.write(repr(exc))
        return -1

    return 0


if __name__ == "__main__":
    sys.exit(main())
