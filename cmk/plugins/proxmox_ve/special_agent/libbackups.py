# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import re
from collections.abc import (
    Callable,
    Collection,
    Generator,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from cmk.utils.paths import tmp_dir

from cmk.plugins.proxmox_ve.special_agent.libproxmox import (
    LogData,
    ProxmoxVeAPI,
    TaskInfo,
)
from cmk.special_agents.v0_unstable.argument_parsing import Args
from cmk.special_agents.v0_unstable.misc import to_bytes
from cmk.special_agents.v0_unstable.storage import Storage

LOGGER = logging.getLogger("agent_proxmox_ve.backups")

BackupInfo = MutableMapping[str, Any]
LogCacheFilePath = tmp_dir / "special_agents" / "agent_proxmox_ve"


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
    storage = Storage(program_ident="agent_proxmox_ve", host=args.hostname)
    with JsonCachedData(
        storage=storage,
        storage_key="upid.log.cache.json",
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


@contextmanager
def JsonCachedData(
    storage: Storage,
    storage_key: str,
    cutoff_condition: Callable[[str, Any], bool],
) -> Generator[Callable[[str, Any], Any], None, None]:
    """Store JSON-serializable data on filesystem and provide it if available"""

    cache = json.loads(storage.read(key=storage_key, default="{}"))
    LOGGER.debug("Cache: loaded %d elements", len(cache))

    dirty = False
    # note: this must not be a generator - otherwise we modify a dict while iterating it
    for key in [k for k, data in cache.items() if cutoff_condition(k, data)]:
        dirty = True
        LOGGER.debug("Cache: erase log cache for %r", key)
        del cache[key]

    def setdefault(key: str, value_fn: Callable[[], Any]) -> Any:
        nonlocal dirty
        if key in cache:
            return cache[key]
        dirty = True
        LOGGER.debug("Cache: %r not found - fetch it", key)
        return cache.setdefault(key, value_fn())

    try:
        yield setdefault
    finally:
        if dirty:
            LOGGER.debug("Cache: write file: %r", storage_key)
            storage.write(storage_key, json.dumps(cache, indent=2))
