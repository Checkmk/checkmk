#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plug-in is notorious for being an exception to just about every rule   #
#   or best practice that applies to check plug-in development.                         #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import ast
import socket
import time
from collections import defaultdict
from collections.abc import Container, Generator, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import quote as url_quote

import cmk.ccc.debug  # pylint: disable=cmk-module-layer-violation
from cmk.ccc.hostaddress import HostName  # pylint: disable=cmk-module-layer-violation

import cmk.utils.paths  # pylint: disable=cmk-module-layer-violation

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation
from cmk.ec.event import (  # pylint: disable=cmk-module-layer-violation
    create_event_from_syslog_message,
)

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
)

from . import commons as logwatch

_MAX_SPOOL_SIZE = 1024**2

_EC_CONNECTION_TIMEOUT = 5  # seconds


CHECK_DEFAULT_PARAMETERS: logwatch.PreDictLogwatchEc = {
    "facility": 17,  # default to "local1"
    "method": "",  # local site
    "monitor_logfilelist": False,
    "monitor_logfile_access_state": 2,
    # These next two entries will be postprocessed by the backend.
    # Don't try this hack at home, we are trained professionals.
    "service_level": ("cmk_postprocessed", "service_level", None),
    "host_name": ("cmk_postprocessed", "host_name", None),
}


def discover_group(section: logwatch.Section, params: Mapping[str, str]) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(
        section, logwatch.RulesetAccess.logwatch_ec_all(params["host_name"]), "groups"
    )


def check_logwatch_ec(
    params: logwatch.ParameterLogwatchEc, section: logwatch.Section
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        None,
        params,
        {None: section},
        check_plugin_logwatch_ec,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(None, HostName(params["host_name"])),
    )


def cluster_check_logwatch_ec(
    params: logwatch.ParameterLogwatchEc, section: Mapping[str, logwatch.Section | None]
) -> CheckResult:
    yield from check_logwatch_ec_common(
        None,
        params,
        {k: v for k, v in section.items() if v is not None},
        check_plugin_logwatch_ec,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(None, HostName(params["host_name"])),
    )


check_plugin_logwatch_ec = CheckPlugin(
    name="logwatch_ec",
    service_name="Log Forwarding",
    sections=["logwatch"],
    discovery_function=discover_group,
    discovery_default_parameters={},
    check_function=check_logwatch_ec,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="logwatch_ec",
    cluster_check_function=cluster_check_logwatch_ec,
)


def discover_single(section: logwatch.Section, params: Mapping[str, str]) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(
        section, logwatch.RulesetAccess.logwatch_ec_all(params["host_name"]), "single"
    )


def check_logwatch_ec_single(
    item: str,
    params: logwatch.ParameterLogwatchEc,
    section: logwatch.Section,
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {None: section},
        check_plugin_logwatch_ec_single,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(item, HostName(params["host_name"])),
    )


def cluster_check_logwatch_ec_single(
    item: str,
    params: logwatch.ParameterLogwatchEc,
    section: Mapping[str, logwatch.Section | None],
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {k: v for k, v in section.items() if v is not None},
        check_plugin_logwatch_ec_single,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(item, HostName(params["host_name"])),
    )


check_plugin_logwatch_ec_single = CheckPlugin(
    name="logwatch_ec_single",
    service_name="Log %s",
    sections=["logwatch"],
    discovery_function=discover_single,
    check_function=check_logwatch_ec_single,
    # other params are added during discovery.
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    cluster_check_function=cluster_check_logwatch_ec_single,
)


# OK      -> priority 5 (notice)
# WARN    -> priority 4 (warning)
# CRIT    -> priority 2 (crit)
# context -> priority 6 (info)
# u = Uknown
def logwatch_to_prio(level: str) -> int:
    if level == "W":
        return 4
    if level == "C":
        return 2
    if level == "O":
        return 5
    if level == ".":
        return 6
    return 4


def _logwatch_inventory_mode_rules(
    forward_settings: Sequence[logwatch.ParameterLogwatchEc],
) -> tuple[Literal["no", "single", "groups"], logwatch.CommonLogwatchEc]:
    merged_rules: logwatch.CommonLogwatchEc = {}
    for rule in forward_settings[-1::-1]:
        merged_rules.update(rule)

    if forward_settings and not merged_rules.get("activation", True):
        return "no", {}  # Configured "activation" to be False.

    if merged_rules.get("separate_checks", False):
        return "single", merged_rules
    return "groups", merged_rules


def discover_logwatch_ec_common(
    section: logwatch.Section,
    params: Sequence[logwatch.ParameterLogwatchEc],
    use_mode: str,
) -> DiscoveryResult:
    log_filter = logwatch.LogFileFilter(params)
    if not (
        forwarded_logs := {
            item for item in logwatch.discoverable_items(section) if log_filter.is_forwarded(item)
        }
    ):
        return

    mode, merged_rules = _logwatch_inventory_mode_rules(params)
    if mode != use_mode:
        return

    if mode == "groups":
        yield Service(
            parameters={"expected_logfiles": sorted(forwarded_logs)},
            labels=logwatch.NEVER_DISCOVER_SERVICE_LABELS,
        )
        return

    single_log_params = logwatch.CommonLogwatchEc()
    for key in [
        "activation",
        "method",
        "facility",
        "monitor_logfilelist",
        "monitor_logfile_access_state",
        "logwatch_reclassify",
    ]:
        if key in merged_rules:
            single_log_params[key] = merged_rules[key]  # type: ignore[literal-required]
    for log in forwarded_logs:
        single_log_params["expected_logfiles"] = [log]
        yield Service(
            item=log,
            parameters=single_log_params.copy(),
            labels=logwatch.NEVER_DISCOVER_SERVICE_LABELS,
        )


@dataclass
class LogwatchForwardedResult:
    num_forwarded: int = 0
    num_spooled: int = 0
    num_dropped: int = 0
    exception: Exception | None = None


class MessageForwarderProto(Protocol):
    def __call__(
        self,
        method: str | tuple,
        messages: Sequence[ec.SyslogMessage],
        timestamp: float,
    ) -> LogwatchForwardedResult: ...


UsedLogFiles = MutableMapping[str, list[tuple[str | None, str]]]


def _get_missing_logfile_from_attr(
    log_file_name: str, node_attrs: Sequence[tuple[str | None, str]]
) -> str | None:
    missing_nodes = [node_name for (node_name, node_attr) in node_attrs if node_attr == "missing"]
    if not missing_nodes:
        return None
    if missing_node_names := [x for x in missing_nodes if x is not None]:
        return f"{log_file_name} (on {', '.join(missing_node_names)})"
    return log_file_name


def _get_missing_logfiles_from_attr(used_logfiles: UsedLogFiles) -> Sequence:
    return [
        summary
        for name, node_attrs in used_logfiles.items()
        if (summary := _get_missing_logfile_from_attr(name, node_attrs))
    ]


def _filter_accumulated_lines(
    cluster_section: logwatch.ClusterSection,
    item: str,
    seen_batches: Container[str],
) -> Iterable[str]:
    yield from (
        line
        for node_data in cluster_section.values()
        if (item_data := node_data.logfiles.get(item)) is not None
        for line in logwatch.extract_unseen_lines(item_data["lines"], seen_batches)
        if line[0] not in (".", "I") and len(line) > 1
    )


def check_logwatch_ec_common(
    item: str | None,
    params: logwatch.ParameterLogwatchEc,
    parsed: logwatch.ClusterSection,
    plugin: CheckPlugin,
    *,
    value_store: MutableMapping[str, Any],
    message_forwarder: MessageForwarderProto,
) -> CheckResult:
    timestamp = time.time()
    yield from logwatch.check_errors(parsed)

    host_name = params["host_name"]

    log_filter = logwatch.LogFileFilter([params])

    if item:
        # If this check has an item (logwatch.ec_single), only forward the information from this log
        if not any(
            item in node_data.logfiles for node_data in parsed.values()
        ) or not log_filter.is_forwarded(item):
            return

        used_logfiles: UsedLogFiles = defaultdict(list)
        for node_name, node_data in parsed.items():
            if item in node_data.logfiles:
                used_logfiles[item].append((node_name, node_data.logfiles[item]["attr"]))

    else:
        used_logfiles = defaultdict(list)
        # Filter logfiles if some should be excluded
        for node_name, node_data in parsed.items():
            for name, data in node_data.logfiles.items():
                if log_filter.is_forwarded(name):
                    used_logfiles[name].append((node_name, data["attr"]))
        used_logfiles = dict(sorted(used_logfiles.items()))

    for logfile in used_logfiles:
        yield from logwatch.check_unreadable_files(
            logwatch.get_unreadable_logfiles(logfile, parsed),
            State(params["monitor_logfile_access_state"]),
        )

    # Check if the number of expected files matches the actual one
    if params["monitor_logfilelist"]:
        yield from _monitor_logile_list(used_logfiles, params.get("expected_logfiles"))

    # 3. create syslog message of each line
    # <128> Oct 24 10:44:27 Klappspaten /var/log/syslog: Oct 24 10:44:27 Klappspaten logger: asdasas
    # <facility+priority> timestamp hostname logfile: message
    facility = params["facility"]
    syslog_messages = []
    forwarded_logfiles = set()

    # Keep track of reclassifed lines
    rclfd_total = 0
    rclfd_to_ignore = 0

    reclassify = bool(params.get("logwatch_reclassify"))

    seen_batches = logwatch.update_seen_batches(value_store, parsed, used_logfiles)
    for logfile in used_logfiles:
        lines = _filter_accumulated_lines(parsed, logfile, seen_batches)

        # Determine logwatch patterns specifically for this logfile
        rules_for_this_file = logwatch.RulesetAccess.logwatch_rules_all(
            host_name=host_name, plugin=plugin, logfile=logfile
        )
        logfile_reclassify_settings = (
            logwatch.compile_reclassify_params(rules_for_this_file) if reclassify else None
        )

        for line in lines:
            rclfd_level = None
            if logfile_reclassify_settings:
                old_level, _text = line.split(" ", 1)
                level = logwatch.reclassify(logfile_reclassify_settings, line[2:], old_level)
                if level != old_level:
                    rclfd_total += 1
                    rclfd_level = level
                    if level == "I":  # Ignored lines are not forwarded
                        rclfd_to_ignore += 1
                        continue

            syslog_messages.append(
                ec.SyslogMessage(
                    facility=facility,
                    severity=logwatch_to_prio(rclfd_level or line[0]),
                    timestamp=int(timestamp),
                    host_name=host_name,
                    application=logfile,
                    text=line[2:],
                    service_level=params["service_level"],
                )
            )
            forwarded_logfiles.add(logfile)

    try:
        if forwarded_logfiles:
            logfile_info = " from " + ", ".join(sorted(forwarded_logfiles))
        else:
            logfile_info = ""

        result = message_forwarder(params["method"], syslog_messages, timestamp)

        yield Result(
            state=State.OK,
            summary="Forwarded %d messages%s" % (result.num_forwarded, logfile_info),
        )
        yield Metric("messages", result.num_forwarded)

        exc_txt = " (%s)" % result.exception if result.exception else ""

        if result.num_spooled:
            yield Result(
                state=State.WARN,
                summary="Spooled %d messages%s" % (result.num_spooled, exc_txt),
            )

        if result.num_dropped:
            yield Result(
                state=State.CRIT,
                summary="Dropped %d messages%s" % (result.num_dropped, exc_txt),
            )

    except Exception as exc:
        if cmk.ccc.debug.enabled():
            raise
        yield Result(
            state=State.CRIT,
            summary="Failed to forward messages (%s). Lost %d messages."
            % (exc, len(syslog_messages)),
        )

    if rclfd_total:
        yield Result(
            state=State.OK,
            summary="Reclassified %d messages through logwatch patterns (%d to IGNORE)"
            % (rclfd_total, rclfd_to_ignore),
        )


def _monitor_logile_list(
    used_logfiles: UsedLogFiles,
    expected_logfiles: Iterable[str] | None,
) -> Iterable[Result]:
    if expected_logfiles is None:
        yield Result(
            state=State.WARN,
            summary=(
                "You enabled monitoring the list of forwarded logfiles. "
                "You need to redo service discovery."
            ),
        )
        return
    missing = [
        *_get_missing_logfiles_from_attr(used_logfiles),
        *(f for f in expected_logfiles if f not in used_logfiles),
    ]
    if missing:
        yield Result(
            state=State.WARN,
            summary="Missing logfiles: %s" % (", ".join(missing)),
        )

    exceeding = [f for f in used_logfiles if f not in expected_logfiles]
    if exceeding:
        yield Result(
            state=State.WARN,
            summary="Newly appeared logfiles: %s" % (", ".join(exceeding)),
        )


# send messages to event console
# a) local in same omd site
# b) local pipe
# c) remote via udp
# d) remote via tcp
@dataclass(frozen=True)
class MessageForwarder:
    item: str | None
    hostname: HostName

    def __call__(
        self,
        method: str | tuple,
        messages: Sequence[ec.SyslogMessage],
        timestamp: float,
    ) -> LogwatchForwardedResult:
        if not method:
            method = str(cmk.utils.paths.omd_root / "tmp/run/mkeventd/eventsocket")
        elif isinstance(method, str) and method == "spool:":
            method += str(cmk.utils.paths.omd_root / "var/mkeventd/spool")

        if isinstance(method, tuple):
            return self._forward_tcp(
                method,
                messages,
                timestamp,
            )

        if not method.startswith("spool:"):
            return self._forward_unix_socket(
                Path(method),
                messages,
            )

        return self._forward_spool_directory(method, messages, timestamp)

    # write into local UNIX socket
    # Important: When the event daemon is stopped, then the socket
    # is *not* existing! This prevents us from hanging in such
    # situations. So we must make sure that we do not create a file
    # instead of the socket!
    @staticmethod
    def _forward_unix_socket(
        path: Path,
        events: Sequence[ec.SyslogMessage],
    ) -> LogwatchForwardedResult:
        try:
            ec.forward_to_unix_socket(events, path, _EC_CONNECTION_TIMEOUT)
        except Exception as exc:
            return LogwatchForwardedResult(exception=exc)
        return LogwatchForwardedResult(num_forwarded=len(events))

    # Spool the log messages to given spool directory.
    # First write a file which is not read into ec, then
    # perform the move to make the file visible for ec
    def _forward_spool_directory(
        self,
        method: str,
        syslog_messages: Sequence[ec.SyslogMessage],
        timestamp: float,
    ) -> LogwatchForwardedResult:
        if not syslog_messages:
            return LogwatchForwardedResult()

        split_files = self._split_file_messages(
            message + "\n" for message in map(repr, syslog_messages)
        )
        for file_index, file_content in enumerate(split_files):
            spool_file = self._get_new_spool_file(method, file_index, timestamp)
            with spool_file.open("w") as f:
                for message in file_content:
                    f.write(message)
            spool_file.rename(spool_file.parent / spool_file.name[1:])

        return LogwatchForwardedResult(num_forwarded=len(syslog_messages))

    @staticmethod
    def _split_file_messages(file_messages: Generator[str, None, None]) -> list[list[str]]:
        result: list[list[str]] = [[]]
        curr_file_index = 0
        curr_character_count = 0
        for file_message in file_messages:
            if curr_character_count >= _MAX_SPOOL_SIZE:
                result.append([])
                curr_file_index += 1
                curr_character_count = 0
            result[curr_file_index].append(file_message)
            curr_character_count += len(file_message)

        return result

    def _get_new_spool_file(
        self,
        method: str,
        file_index: int,
        timestamp: float,
    ) -> Path:
        spool_file = Path(
            method[6:],
            ".%s_%s%d_%d"
            % (
                self.hostname,
                (self.item.replace("/", "\\") + "_") if self.item else "",
                timestamp,
                file_index,
            ),
        )
        spool_file.parent.mkdir(parents=True, exist_ok=True)
        return spool_file

    def _forward_tcp(
        self,
        method: tuple,
        syslog_messages: Sequence[ec.SyslogMessage],
        timestamp: float,
    ) -> LogwatchForwardedResult:
        # Transform old format: (proto, address, port)
        if not isinstance(method[1], dict):
            method = (method[0], {"address": method[1], "port": method[2]})

        result = LogwatchForwardedResult()

        message_chunks = []

        if self._shall_spool_messages(method):
            message_chunks += self._load_spooled_messages(method, result, timestamp)

        # Add chunk of new messages (when there are new ones)
        if syslog_messages:
            message_chunks.append((timestamp, 0, list(map(repr, syslog_messages))))

        if not message_chunks:
            return result  # Nothing to process

        try:
            self._forward_send_tcp(method, message_chunks, result)
        except Exception as exc:
            result.exception = exc

        # result.exception may be set in the line above, or inside _forward_send_tcp
        if result.exception:
            if self._shall_spool_messages(method):
                self._spool_messages(message_chunks, result)
            else:
                result.num_dropped = sum(len(c[2]) for c in message_chunks)

        return result

    @staticmethod
    def _shall_spool_messages(method: object) -> bool:
        return (
            isinstance(method, tuple)
            and method[0] == "tcp"
            and isinstance(method[1], dict)
            and "spool" in method[1]
        )

    @staticmethod
    def _forward_send_tcp(
        method: tuple,
        message_chunks: Iterable[tuple[float, int, list[str]]],
        result: LogwatchForwardedResult,
    ) -> None:
        protocol, method_params = method

        if protocol == "udp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        elif protocol == "tcp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            raise NotImplementedError()

        sock.settimeout(_EC_CONNECTION_TIMEOUT)
        sock.connect((method_params["address"], method_params["port"]))

        try:
            for _time_spooled, _num_spooled, message_chunk in message_chunks:
                for message in message_chunk:
                    sock.sendall(message.encode("utf-8") + b"\n")
                    result.num_forwarded += 1
        except Exception as exc:
            result.exception = exc
        finally:
            sock.close()

    # a) Rewrite chunks that have been processed partially
    # b) Write files for new chunk
    def _spool_messages(
        self,
        message_chunks: Iterable[tuple[float, int, list[str]]],
        result: LogwatchForwardedResult,
    ) -> None:
        self._spool_path.mkdir(parents=True, exist_ok=True)

        # Now write updated/new and delete emtpy spool files
        for time_spooled, num_already_spooled, message_chunk in message_chunks:
            spool_file_path = self._spool_path / ("spool.%0.2f" % time_spooled)

            if not message_chunk:
                # Cleanup empty spool files
                spool_file_path.unlink(missing_ok=True)
                continue

            try:
                # Partially processed chunks or the new one
                spool_file_path.write_text(repr(message_chunk))
                result.num_spooled += len(message_chunk)
            except Exception:
                if cmk.ccc.debug.enabled():
                    raise

                if num_already_spooled == 0:
                    result.num_dropped += len(message_chunk)

    def _update_logwatch_spoolfiles(
        self,
        old_location: Path,
    ) -> None:
        # can be removed with checkmk 2.4.0
        if self.item is None:
            # no need to update the spoolfiles if separate_checks = False
            return
        for path in old_location.glob("spool.*"):
            time_spooled = float(path.name[6:])
            messages = ast.literal_eval(path.read_text())
            if len(messages) == 0:
                continue
            event = create_event_from_syslog_message(messages[0].encode("utf-8"), None, None)
            if event["application"] == self.item:
                result = LogwatchForwardedResult()
                self._spool_messages([(time_spooled, 0, messages)], result)
                path.unlink()

    def _load_spooled_messages(
        self,
        method: tuple,
        result: LogwatchForwardedResult,
        timestamp: float,
    ) -> list[tuple[float, int, list[str]]]:
        spool_params = method[1]["spool"]

        self._update_logwatch_spoolfiles(
            old_location=self._get_spool_path(self.hostname, None),
        )

        try:
            spool_files = sorted(self._spool_path.iterdir())
        except FileNotFoundError:
            return []

        message_chunks = []

        total_size = 0
        for path in spool_files:
            # Delete unknown files
            if not path.name.startswith("spool."):
                path.unlink()
                continue

            time_spooled = float(path.name[6:])
            file_size = path.stat().st_size
            total_size += file_size

            # Delete fully processed files
            if file_size in [0, 2]:
                path.unlink()
                continue

            # TODO: this seems strange: we already added the filesize to the total_size, but now we
            # delete the file? this way total_size is too big?!

            # Delete too old files by age
            if time_spooled < timestamp - spool_params["max_age"]:
                self._spool_drop_messages(path, result)
                continue

        # Delete by size till half of target size has been deleted (oldest spool files first)
        if total_size > spool_params["max_size"]:
            target_size = int(spool_params["max_size"] / 2.0)

            for filename in spool_files:
                total_size -= self._spool_drop_messages(filename, result)
                if target_size >= total_size:
                    break  # cleaned up enough

        # Now process the remaining files
        for path in spool_files:
            time_spooled = float(path.name[6:])

            try:
                messages = ast.literal_eval(path.read_text())
                path.unlink()
            except FileNotFoundError:
                continue

            message_chunks.append((time_spooled, len(messages), messages))

        return message_chunks

    @staticmethod
    def _spool_drop_messages(path: Path, result: LogwatchForwardedResult) -> int:
        messages = ast.literal_eval(path.read_text())
        result.num_dropped += len(messages)

        file_size = path.stat().st_size
        path.unlink()
        return file_size

    @property
    def _spool_path(self) -> Path:
        return self._get_spool_path(self.hostname, self.item)

    @staticmethod
    def _get_spool_path(hostname: str, item: str | None) -> Path:
        result = cmk.utils.paths.var_dir / "logwatch_spool" / hostname
        return result if item is None else (result / f"item_{url_quote(item, safe='')}")
