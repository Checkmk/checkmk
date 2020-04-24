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
# - agent: cuttoff-weeks / cert-check / timeout configurable
# - Turn into Python3-Script:
#   - use Python3 type annotations
#   - use {**a,**b} instead of .update()
#   - use (*, arg1, arg2..) syntax
#   - use suppress
#   - super()
# - Replication Status VMs & Container, Gesamtstatus + piggybacked
# - Snapshots - piggybacked

# Read:
# - https://pve.proxmox.com/wiki/Proxmox_VE_API
# - https://pve.proxmox.com/pve-docs/api-viewer/
# - https://pve.proxmox.com/pve-docs/api-viewer/apidoc.js
# - https://pypi.org/project/proxmoxer/

# pylint: disable=too-few-public-methods

import sys
import json
import argparse
import logging
import re
# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error
from datetime import datetime, timedelta
import time  # todo(Python3): not needed any more
from contextlib import contextmanager
from typing import Any, List, Dict, Union, Optional, Tuple, Sequence, Generator

import six  # todo(Python3): not needed any more
import requests
from requests.packages import urllib3

import cmk.utils.password_store
from cmk.utils.paths import tmp_dir

# cannot be imported yet - pathlib2 is missing for python3
# from cmk.special_agents.utils import vcrtrace

LOGGER = logging.getLogger("agent_proxmox")

ListOrDict = Union[List[Dict[str, Any]], Dict[str, Any]]
StrSequence = Union[List[str], Tuple[str]]

LogCacheFilePath = Path(tmp_dir) / "special_agents" / "agent_proxmox"


def parse_arguments(argv):
    # type: (List[str]) -> argparse.Namespace
    """parse command line arguments and return argument object"""
    parser = argparse.ArgumentParser(description=__doc__)
    # needs import vcrtrace which needs pathlib2
    # parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[('authorization', '****')]))
    parser.add_argument('--timeout', '-t', type=int, default=20, help='API call timeout')
    parser.add_argument('--port', type=int, default=8006, help='IPv4 port to connect to')
    parser.add_argument('--username', '-u', type=str, help='username for connection')
    parser.add_argument('--password', '-p', type=str, help='password for connection')
    parser.add_argument('--verbose', '-v', action="count", default=0)
    # TODO: warn if log-cutoff-weeks is shorter than actual log length or
    #       shorter than configured check
    parser.add_argument('--log-cutoff-weeks',
                        type=int,
                        default=2,
                        help='Fetch logs N weeks back in time')
    # TODO: default should not be True
    parser.add_argument('--no-cert-check', action="store_true", default=True)
    parser.add_argument('--debug', action="store_true", help="Keep some exceptions unhandled")
    parser.add_argument("hostname", help="Name of the Proxmox instance to query.")
    return parser.parse_args(argv)


class BackupTask:
    """Handles a bunch of log lines and turns them into a set of data needed from the log
    """
    class LogParseError(RuntimeError):
        def __init__(self, line, msg):
            # type: (int, str) -> None
            # todo(Python3): super()
            RuntimeError.__init__(self, msg)
            self.line = line

        def __repr__(self):
            # type: () -> str
            # todo(Python3): super()
            return "LogParseError(%d, %r)" % (self.line, RuntimeError.__str__(self))

    def __init__(self, task, logs):
        # type: (Dict[str, Any], Sequence[Dict[str, Any]]) -> None
        self.upid, self.type, self.starttime, self.status = "", "", 0, ""
        self.__dict__.update(task)

        try:
            self.backup_data = self._extract_logs(self._to_lines(logs))
        except self.LogParseError as exc:
            self.backup_data = {}
            LOGGER.error("Parsing the log with UPID=%r resulted in a LogParseError in line %d: %r",
                         task["upid"], exc.line, str(exc))
            LOGGER.error(">>>>>> content")
            for line in logs:
                LOGGER.error(">> %s", line["t"])
            LOGGER.error("<<<<<< content")

    @staticmethod
    def _to_lines(lines_with_numbers):
        # type: (Sequence[Dict[str, Any]]) -> Sequence[str]
        """ Gets list of dict containing a line number an a line [{"n": int, "t": str}*]
        Returns List of lines only"""
        return tuple(  #
            line  #
            for elem in lines_with_numbers  #
            for line in (elem["t"],)  #
            if isinstance(line, six.string_types) and line.strip())

    def __str__(self):
        # type: () -> str
        return "BackupTask(%r, t=%r, vms=%r)" % (
            self.type,
            datetime.fromtimestamp(self.starttime).strftime("%Y.%m.%d-%H:%M:%S"),
            tuple(self.backup_data.keys()),
        )

    @staticmethod
    def _extract_tuple(pattern, string, count):
        # type: (str, str, int) -> Optional[Sequence[str]]
        """return regex-findings as tuple.
        Return tuple of None (or single None) if @string does not match @pattern"""
        result = re.search(pattern, string, flags=re.IGNORECASE)
        return None if result is None else result.groups()[:count]

    @staticmethod
    def _extract_value(pattern, string):
        # type: (str, str) -> Optional[str]
        """Return first regex-group finding as string if available"""
        result = BackupTask._extract_tuple(pattern, string, 1)
        return None if result is None else result[0]

    @staticmethod
    def _extract_logs(logs):
        # type: (Sequence[str]) -> Dict[str, Any]
        pattern = {
            "start_job": r"^INFO: starting new backup job: vzdump (.*)",
            "start_vm": r"^INFO: Starting Backup of VM (\d+).*",
            "started_time": r"^INFO: Backup started at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            "finish_vm": r"^INFO: Finished Backup of VM (\d+) \((\d{2}:\d{2}:\d{2})\).*",
            "error_vm": r"^ERROR: Backup of VM (\d+) failed - (.*)$",
            "create_archive": r"^INFO: creating archive '(.*)'",
            "bytes_written": r"^INFO: Total bytes written: (\d+) \(.*, (.*)\/s\)",
            "transferred": r"^INFO: transferred (\d+) MB in (\d+) seconds \(.*\)",
            "archive_size": r"^INFO: archive file size: (.*)",
        }

        result = {}  # type: Dict[str, Any]
        current_vmid = ""  # type: str
        current_dataset = {}  # type: Dict[str, Any]

        for linenr, line in enumerate(logs):
            start_vmid = BackupTask._extract_value(pattern["start_vm"], line)
            if start_vmid is not None:
                if current_vmid:
                    raise BackupTask.LogParseError(
                        linenr,
                        "Captured start of rocessing VM %r while VM %r is still active" %
                        (start_vmid, current_vmid),
                    )
                current_vmid = start_vmid
                current_dataset = {}
                continue

            stop_vmid = BackupTask._extract_value(pattern["finish_vm"], line)
            if stop_vmid is not None:
                if stop_vmid != current_vmid:
                    raise BackupTask.LogParseError(
                        linenr,
                        "Found end of VM %r while another VM %r was active" % (  #
                            stop_vmid, current_vmid))
                result[current_vmid] = current_dataset
                if not all(key in current_dataset for key in (  #
                        "transfer_size", "transfer_time", "archive_name", "archive_size",
                        "started_time")):
                    raise BackupTask.LogParseError(
                        linenr,
                        "End of VM %r while still information is missing (have %r)" % (  #
                            current_vmid, tuple(current_dataset.keys())))
                current_vmid = ""
                continue

            error_vm = BackupTask._extract_tuple(pattern["error_vm"], line, 2)
            if error_vm is not None:
                error_vmid, error_msg = error_vm
                if current_vmid and error_vmid != current_vmid:
                    raise BackupTask.LogParseError(
                        linenr,
                        "Error for VM %r while another VM %r was active" % (  #
                            error_vmid, current_vmid))
                LOGGER.warning("Found error for VM %r: %r", error_vmid, error_msg)
                # todo: store erroneous backup status
                current_vmid = ""
                continue

            started_time = BackupTask._extract_value(pattern["started_time"], line)
            if started_time is not None:
                if not current_vmid:
                    raise BackupTask.LogParseError(linenr,
                                                   "Found start date while no VM was active")
                current_dataset["started_time"] = started_time
                continue

            bytes_written = BackupTask._extract_tuple(pattern["bytes_written"], line, 2)
            if bytes_written is not None:
                vm_size = int(bytes_written[0])
                bandw = to_bytes(bytes_written[1])
                if not current_vmid:
                    raise BackupTask.LogParseError(
                        linenr, "Found bandwidth information while no VM was active")
                current_dataset["transfer_size"] = vm_size
                current_dataset["transfer_time"] = round(vm_size / bandw) if bandw > 0 else 0
                continue

            transferred = BackupTask._extract_tuple(pattern["transferred"], line, 2)
            if transferred is not None:
                transfer_size_mb, transfer_time = transferred
                if not current_vmid:
                    raise BackupTask.LogParseError(
                        linenr, "Found bandwidth information while no VM was active")
                current_dataset["transfer_size"] = int(transfer_size_mb) * (1 << 20)
                current_dataset["transfer_time"] = int(transfer_time)
                continue

            archive_name = BackupTask._extract_value(pattern["create_archive"], line)
            if archive_name is not None:
                if not current_vmid:
                    raise BackupTask.LogParseError(  #
                        linenr, "Found archive name without active VM")
                current_dataset["archive_name"] = archive_name
                continue

            archive_size = BackupTask._extract_value(pattern["archive_size"], line)
            if archive_size is not None:
                if not current_vmid:
                    raise BackupTask.LogParseError(
                        linenr, "Found archive size information without active VM")
                current_dataset["archive_size"] = to_bytes(archive_size)
                continue
        assert current_vmid == ""
        return result


@contextmanager
def JsonCachedData(filename):
    # type: (str) -> Generator[Dict[str, Any], None, None]
    """Store JSON-serializable data on filesystem and provide it if available"""
    # # todo(python3): use exist_ok=True, remove try/except
    try:
        LogCacheFilePath.mkdir(parents=True)
    except OSError as exc:
        # todo(python3): use FileExistsError - 17 is not portable
        if exc.errno != 17:
            raise
    cache_file = LogCacheFilePath / filename
    try:
        with cache_file.open() as crfile:
            cache = json.load(crfile)
    # todo(python3): ValueError->JSONDecodeError
    except (IOError, ValueError):
        cache = {}
    try:
        yield cache
    finally:
        Path()
        LOGGER.info("Write cache file: %r", str(cache_file.absolute()))
        # todo(python3): use "w" only
        # todo(python3): use json.dump()
        with cache_file.open(mode="wb") as cwfile:
            cwfile.write(json.dumps(cache).encode())


def fetch_backup_data(args, session, nodes):
    # type: (argparse.Namespace, ProxmoxAPI, Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]
    """Since the Proxmox API does not provide us with information about past backups we read the
    information we need from log entries created for each backup process"""
    # Fetching log files is by far the most time consuming process issued by the Proxmox agent.
    # Since logs have a unique UPID we can safely cache them
    with JsonCachedData("upid.log.cache.json") as cache:
        # todo(python3): don't use time.mktime
        cutoff_date = int(
            time.mktime(  #
                (datetime.now() - timedelta(weeks=args.log_cutoff_weeks)).timetuple()))
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
                        })["nodes"][node["node"]]["tasks"][task["upid"]]["log"]))[1])
            for node in nodes
            for task in node["tasks"]
            if (task['type'] == "vzdump" and int(task['starttime']) >= cutoff_date))

        backup_data = {}  # type: Dict[str, Dict[str, Any]]
        for task in backup_tasks:
            LOGGER.info("%s", task)
            LOGGER.debug("%r", task.backup_data)
            for vmid, bdata in task.backup_data.items():
                if vmid in backup_data:
                    continue
                backup_data[vmid] = bdata

        return backup_data


def to_bytes(string):
    # type: (str) -> int
    """Turn a string containing a byte-size with units like (MiB, ..) into an int
    containing the size in bytes"""
    return round(  #
        (float(string[:-3]) * (1 << 10)) if string.endswith("KiB") else  #
        (float(string[:-2]) * (1 << 10)) if string.endswith("KB") else  #
        (float(string[:-3]) * (1 << 20)) if string.endswith("MiB") else  #
        (float(string[:-2]) * (1 << 20)) if string.endswith("MB") else  #
        (float(string[:-3]) * (1 << 30)) if string.endswith("GiB") else  #
        (float(string[:-2]) * (1 << 30)) if string.endswith("GB") else  #
        float(string))


def write_agent_output(args):
    # type: (argparse.Namespace) -> None
    """Fetches and writes selected information formatted as agent output to stdout"""
    def write_piggyback_sections(host, sections):
        # type: (str, Sequence[Dict[str, Any]]) -> None
        print("<<<<%s>>>>" % host)
        write_sections(sections)
        print("<<<<>>>>")

    def write_sections(sections):
        # type: (Sequence[Dict[str, Any]]) -> None
        def write_section(name, data, skip=False, jsonify=True):
            # type: (str, Any, bool, bool) -> None
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
        assert node["type"] == 'node'
        write_piggyback_sections(
            host=node['node'],
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
                                "status", "checktime", "key", "level", "nextduedate", "productname",
                                "regdate"
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
            ])

    for vmid, vm in all_vms.items():
        write_piggyback_sections(
            host=vm["name"],
            sections=[
                # {  # Todo
                #    "name": "proxmox_vm_info",
                # },
                {
                    "name": "proxmox_disk_usage",
                    "data": {
                        "disk": vm["disk"],
                        "max_disk": vm["maxdisk"],
                    },
                    "skip": vm["type"] == 'qemu',
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
            ])


class ProxmoxSession:
    """Session"""
    class HTTPAuth(requests.auth.AuthBase):
        """Auth"""
        def __init__(self, base_url, credentials, timeout, verify_ssl):
            # type: (str, Dict[str, str], int, bool) -> None
            super(ProxmoxSession.HTTPAuth, self).__init__()
            ticket_url = base_url + "api2/json/access/ticket"
            response = requests.post(url=ticket_url,
                                     verify=verify_ssl,
                                     data=credentials,
                                     timeout=timeout).json().get("data")
            if response is None:
                raise RuntimeError("Couldn't authenticate %r @ %r" %
                                   (credentials.get('username', "no-username"), ticket_url))

            self.pve_auth_cookie = response["ticket"]
            self.csrf_prevention_token = response["CSRFPreventionToken"]

        def __call__(self, r):
            # type: (requests.PreparedRequest) -> requests.PreparedRequest
            r.headers["CSRFPreventionToken"] = self.csrf_prevention_token
            return r

    def __init__(self, endpoint, credentials, timeout, verify_ssl):
        # type: (Tuple[str, int], Dict[str, str], int, bool) -> None
        def create_session():
            # type: () -> requests.Session
            session = requests.Session()
            session.auth = self.HTTPAuth(self._base_url, credentials, timeout, verify_ssl)
            session.cookies = requests.cookies.cookiejar_from_dict(  # type: ignore
                {"PVEAuthCookie": session.auth.pve_auth_cookie})
            session.headers['Connection'] = 'keep-alive'
            session.headers["accept"] = ", ".join(
                ("application/json", "application/x-javascript", "text/javascript",
                 "text/x-javascript", "text/x-json"))
            return session

        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._base_url = "https://%s:%d/" % endpoint
        self._session = create_session()

    def __enter__(self):
        # type: () -> Any
        return self

    def __exit__(self, *args, **kwargs):  # wing disable:argument-not-used
        # type: (Any, Any) -> None
        self.close()

    def close(self):
        # type: () -> None
        """close connection to ProxMox endpoint"""
        if self._session:
            self._session.close()

    def get_raw(self, sub_url):
        # type: (str) -> requests.Response
        return self._session.request(
            method="GET",
            url=self._base_url + sub_url,
            # todo: generic
            params={"limit": "5000"} if
            (sub_url.endswith("/log") or sub_url.endswith("/tasks")) else {},
            verify=self._verify_ssl,
            timeout=self._timeout,
        )

    def get_api_element(self, path):
        # type: (str) -> Any
        """do an API GET request"""
        response_json = self.get_raw("api2/json/" + path).json()
        if 'errors' in response_json:
            raise RuntimeError("Could not fetch %r (%r)" % (path, response_json['errors']))
        return response_json.get('data')


class ProxmoxAPI:
    """Wrapper for ProxmoxSession which provides high level API calls"""
    def __init__(self, host, port, credentials, timeout, verify_ssl):
        # type: (str, int, Any, int, bool) -> None
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

    def __enter__(self):
        # type: () -> Any
        self._session.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        self._session.__exit__(*args, **kwargs)
        self._session.close()

    def get(self, path):
        # type: (Union[str, List[str], Tuple[str]]) -> Any
        """Handle request items in form of 'path/to/item' or ['path', 'to', 'item'] """
        return self._session.get_api_element("/".join(
            str(p) for p in path) if isinstance(path, (list, tuple)) else path)

    def get_tree(self, requested_structure):
        # type: (ListOrDict) -> Any
        def rec_get_tree(element_name, requested_structure, path):
            # type: (Optional[str], ListOrDict, StrSequence) -> Any
            """Recursively fetch data from API to match <requested_structure>"""
            def is_list_of_subtree_names(data):
                # type: (ListOrDict) -> bool
                """Return True if given data is a list of dicts containing names of subtrees,
                e.g [{'name': 'log'}, {'name': 'options'}, ...]"""
                return bool(data) and all(
                    isinstance(elem, dict) and tuple(elem) in {("name",), ("subdir",), ("cmd",)}  #
                    for elem in data)

            def extract_request_subtree(request_tree):
                # type: (ListOrDict) -> ListOrDict
                """If list if given return first (and only) element return the provided data tree"""
                return (request_tree if not isinstance(request_tree, list) else  #
                        next(iter(request_tree)) if len(request_tree) > 0 else {})

            def extract_variable(st):
                # type: (ListOrDict) -> Optional[Dict[str, Any]]
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

            def dict_merge(d1, d2):
                # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Any]
                """Does the same as {**d1, **d2} would do"""
                result = d1.copy()
                result.update(d2)
                return result

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
                                               for identifier in ('name', 'subdir', 'cmd')
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
                        return {
                            key: rec_get_tree(key, subtree[key], next_path)  #
                            for key in subtree
                        } if isinstance(requested_structure, dict) else response

                    assert isinstance(requested_structure, list)
                    return [
                        dict_merge(
                            key,
                            rec_get_tree(
                                key[variable["name"]],
                                variable["subtree"],  #
                                next_path) or {})  #
                        for key in response
                    ]

            return response

        return rec_get_tree(None, requested_structure, [])


def main(argv=None):
    # type: (Any) -> int
    """read arguments, configure application and run command specified on command line"""
    if argv is None:
        cmk.utils.password_store.replace_passwords()
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # type: ignore
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level={
            0: logging.WARN,
            1: logging.INFO,
            2: logging.DEBUG
        }.get(args.verbose, logging.DEBUG),
    )
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    # activate as soon as vcr is available (see imports)
    # logging.getLogger("vcr").setLevel(logging.WARN)
    LOGGER.info("running file %s with Python version %s", __file__,
                ".".join(str(e) for e in sys.version_info))

    try:
        write_agent_output(args)
    except Exception as exc:
        if args.debug:
            raise
        LOGGER.error("Caught exception: %r", exc)
        return -1

    return 0


if __name__ == "__main__":
    sys.exit(main())
