#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plugin is notorious for being an exception to just about every rule    #
#   or best practice that applies to check plugin development.                          #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import ast
import errno
import socket
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Counter,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)

import cmk.utils.debug  # pylint: disable=cmk-module-layer-violation
import cmk.utils.paths  # pylint: disable=cmk-module-layer-violation
from cmk.utils.type_defs import (  # pylint: disable=cmk-module-layer-violation
    CheckPluginName,
    HostName,
)

# from cmk.base.config import logwatch_rules will NOT work!
import cmk.base.config  # pylint: disable=cmk-module-layer-violation

# import from legacy API until we come up with something better
from cmk.base.check_api import (  # pylint: disable=cmk-module-layer-violation
    host_name,
    service_extra_conf,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_value_store,
    Metric,
    register,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import logwatch

from cmk.ec.export import (  # pylint: disable=cmk-module-layer-violation
    SyslogForwarderUnixSocket,
    SyslogMessage,
)

ClusterSection = Dict[Optional[str], logwatch.Section]
_MAX_SPOOL_SIZE = 1024**2

CHECK_DEFAULT_PARAMETERS = {
    "facility": 17,  # default to "local1"
    "method": "",  # local site
    "monitor_logfilelist": False,
    "monitor_logfile_access_state": 2,
}


def discover_group(
    section: logwatch.Section,
) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(section, logwatch.get_ec_rule_params(), "groups")


def check_logwatch_ec(params: Mapping[str, Any], section: logwatch.Section) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        None,
        params,
        {None: section},
        service_level=_get_effective_service_level(CheckPluginName("logwatch_ec"), None),
        value_store=get_value_store(),
        hostname=host_name(),
        message_forwarder=MessageForwarder(None, host_name()),
    )


def cluster_check_logwatch_ec(
    params: Mapping[str, Any],
    section: Mapping[str, Optional[logwatch.Section]],
) -> CheckResult:
    yield from check_logwatch_ec_common(
        None,
        params,
        {k: v for k, v in section.items() if v is not None},
        service_level=_get_effective_service_level(CheckPluginName("logwatch_ec"), None),
        value_store=get_value_store(),
        hostname=host_name(),
        message_forwarder=MessageForwarder(None, host_name()),
    )


register.check_plugin(
    name="logwatch_ec",
    service_name="Log Forwarding",
    sections=["logwatch"],
    discovery_function=discover_group,
    check_function=check_logwatch_ec,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="logwatch_ec",
    cluster_check_function=cluster_check_logwatch_ec,
)


def discover_single(
    section: logwatch.Section,
) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(section, logwatch.get_ec_rule_params(), "single")


def check_logwatch_ec_single(
    item: str,
    params: Mapping[str, Any],
    section: logwatch.Section,
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {None: section},
        service_level=_get_effective_service_level(CheckPluginName("logwatch_ec_single"), item),
        value_store=get_value_store(),
        hostname=host_name(),
        message_forwarder=MessageForwarder(item, host_name()),
    )


def cluster_check_logwatch_ec_single(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[logwatch.Section]],
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {k: v for k, v in section.items() if v is not None},
        service_level=_get_effective_service_level(CheckPluginName("logwatch_ec_single"), item),
        value_store=get_value_store(),
        hostname=host_name(),
        message_forwarder=MessageForwarder(item, host_name()),
    )


register.check_plugin(
    name="logwatch_ec_single",
    service_name="Log %s",
    sections=["logwatch"],
    discovery_function=discover_single,
    check_function=check_logwatch_ec_single,
    check_default_parameters=CHECK_DEFAULT_PARAMETERS,
    cluster_check_function=cluster_check_logwatch_ec_single,
)


# Yet another unbelievable API violation:
def _get_effective_service_level(
    plugin_name: CheckPluginName,
    item: Optional[str],
) -> int:
    """Get the service level that applies to the current service."""

    host = HostName(host_name())
    service_description = cmk.base.config.service_description(host, plugin_name, item)
    config_cache = cmk.base.config.get_config_cache()
    service_level = config_cache.service_level_of_service(host, service_description)
    if service_level is not None:
        return service_level

    return config_cache.get_host_config(host).service_level or 0


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


def _logwatch_inventory_mode_rules(forward_settings) -> Tuple[str, Dict[str, Any]]:
    merged_rules = {}
    for rule in forward_settings[-1::-1]:
        if isinstance(rule, dict):
            for key, value in rule.items():
                merged_rules[key] = value
        elif isinstance(rule, str):
            return "no", {}  # Configured "no forwarding"

    mode = "single" if merged_rules.get("separate_checks", False) else "groups"
    return mode, merged_rules


def discover_logwatch_ec_common(
    section: logwatch.Section,
    params: Sequence[Mapping[str, Any]],
    use_mode: str,
) -> DiscoveryResult:
    discoverable_items = logwatch.discoverable_items(section)
    forwarded_logs = logwatch.select_forwarded(discoverable_items, params)
    if not forwarded_logs:
        return

    mode, merged_rules = _logwatch_inventory_mode_rules(params)
    if mode != use_mode:
        return

    if mode == "groups":
        yield Service(parameters={"expected_logfiles": sorted(forwarded_logs)})
        return

    single_log_params = {}
    for key in [
        "method",
        "facility",
        "monitor_logfilelist",
        "monitor_logfile_access_state",
        "logwatch_reclassify",
    ]:
        if key in merged_rules:
            single_log_params[key] = merged_rules[key]
    for log in forwarded_logs:
        single_log_params["expected_logfiles"] = [log]
        yield Service(item=log, parameters=single_log_params.copy())


class LogwatchFordwardResult:
    def __init__(self, num_forwarded=0, num_spooled=0, num_dropped=0, exception=None) -> None:
        self.num_forwarded = num_forwarded
        self.num_spooled = num_spooled
        self.num_dropped = num_dropped
        self.exception = exception


class MessageForwaderProto(Protocol):
    def __call__(
        self,
        method: Union[str, tuple],
        messages: Sequence[SyslogMessage],
    ) -> LogwatchFordwardResult:
        ...


UsedLogFiles = MutableMapping[str, list[tuple[Optional[str], str]]]


def _get_missing_logfile_from_attr(
    log_file_name: str, node_attrs: Sequence[tuple[Optional[str], str]]
) -> Optional[str]:
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
    cluster_section: ClusterSection,
    item: str,
    value_store: MutableMapping[str, Any],
) -> Iterable[str]:
    yield from (
        line
        for node_data in cluster_section.values()
        if (item_data := node_data.logfiles.get(item)) is not None
        for line in logwatch.extract_unseen_lines(value_store, item_data["lines"])
        if line[0] not in (".", "I") and len(line) > 1
    )


def check_logwatch_ec_common(  # pylint: disable=too-many-branches
    item: Optional[str],
    params: Mapping[str, Any],
    parsed: ClusterSection,
    *,
    service_level: int,
    value_store: MutableMapping[str, Any],
    hostname: HostName,
    message_forwarder: MessageForwaderProto,
) -> CheckResult:
    yield from logwatch.check_errors(parsed)

    if item:
        # If this check has an item (logwatch.ec_single), only forward the information from this log
        if not any(
            item in node_data.logfiles for node_data in parsed.values()
        ) or not logwatch.ec_forwarding_enabled(params, item):
            return

        used_logfiles: UsedLogFiles = defaultdict(list)
        for node_name, node_data in parsed.items():
            if item in node_data.logfiles:
                used_logfiles[item].append((node_name, node_data.logfiles[item]["attr"]))

        yield from logwatch.check_unreadable_files(
            logwatch.get_unreadable_logfiles(item, parsed),
            State(params["monitor_logfile_access_state"]),
        )

    else:
        used_logfiles = defaultdict(list)
        # Filter logfiles if some should be excluded
        for node_name, node_data in parsed.items():
            for name, data in node_data.logfiles.items():
                if logwatch.ec_forwarding_enabled(params, name):
                    used_logfiles[name].append((node_name, data["attr"]))
        used_logfiles = dict(sorted(used_logfiles.items()))

        for logfile in used_logfiles:
            yield from logwatch.check_unreadable_files(
                logwatch.get_unreadable_logfiles(logfile, parsed),
                State(params["monitor_logfile_access_state"]),
            )

    # Check if the number of expected files matches the actual one
    if params["monitor_logfilelist"]:
        if "expected_logfiles" not in params:
            yield Result(
                state=State.WARN,
                summary=(
                    "You enabled monitoring the list of forwarded logfiles. "
                    "You need to redo service discovery."
                ),
            )
        else:
            expected = params["expected_logfiles"]
            missing = [
                *_get_missing_logfiles_from_attr(used_logfiles),
                *(f for f in expected if f not in used_logfiles),
            ]
            if missing:
                yield Result(
                    state=State.WARN,
                    summary="Missing logfiles: %s" % (", ".join(missing)),
                )

            exceeding = [f for f in used_logfiles if f not in expected]
            if exceeding:
                yield Result(
                    state=State.WARN,
                    summary="Newly appeared logfiles: %s" % (", ".join(exceeding)),
                )

    # 3. create syslog message of each line
    # <128> Oct 24 10:44:27 Klappspaten /var/log/syslog: Oct 24 10:44:27 Klappspaten logger: asdasas
    # <facility+priority> timestamp hostname logfile: message
    facility = params["facility"]
    syslog_messages = []
    cur_time = int(time.time())

    forwarded_logfiles = set([])

    # Keep track of reclassifed lines
    rclfd_total = 0
    rclfd_to_ignore = 0

    logfile_reclassify_settings: Dict[str, Any] = {}

    def add_reclassify_settings(settings):
        if isinstance(settings, dict):
            logfile_reclassify_settings["reclassify_patterns"].extend(
                settings.get("reclassify_patterns", [])
            )
            if "reclassify_states" in settings:
                logfile_reclassify_settings["reclassify_states"] = settings["reclassify_states"]
        else:  # legacy configuration
            logfile_reclassify_settings["reclassify_patterns"].extend(settings)

    for logfile in used_logfiles:
        lines = _filter_accumulated_lines(parsed, logfile, value_store)

        logfile_reclassify_settings["reclassify_patterns"] = []
        logfile_reclassify_settings["reclassify_states"] = {}

        # Determine logwatch patterns specifically for this logfile
        if params.get("logwatch_reclassify"):
            logfile_settings = service_extra_conf(
                HostName(host_name()),
                logfile,
                cmk.base.config.logwatch_rules,
            )
            for settings in logfile_settings:
                add_reclassify_settings(settings)

        for line in lines:
            rclfd_level = None
            if logfile_reclassify_settings:
                old_level, _text = line.split(" ", 1)
                level = logwatch.reclassify(
                    Counter(), logfile_reclassify_settings, line[2:], old_level
                )
                if level != old_level:
                    rclfd_total += 1
                    rclfd_level = level
                    if level == "I":  # Ignored lines are not forwarded
                        rclfd_to_ignore += 1
                        continue

            syslog_messages.append(
                SyslogMessage(
                    facility=facility,
                    severity=logwatch_to_prio(rclfd_level or line[0]),
                    timestamp=cur_time,
                    host_name=hostname,
                    application=logfile,
                    text=line[2:],
                    service_level=service_level,
                )
            )
            forwarded_logfiles.add(logfile)

    try:
        if forwarded_logfiles:
            logfile_info = " from " + ", ".join(sorted(forwarded_logfiles))
        else:
            logfile_info = ""

        result = message_forwarder(params["method"], syslog_messages)

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
        if cmk.utils.debug.enabled():
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


# send messages to event console
# a) local in same omd site
# b) local pipe
# c) remote via udp
# d) remote via tcp
@dataclass(frozen=True)
class MessageForwarder:
    item: Optional[str]
    hostname: HostName

    def __call__(
        self,
        method: Union[str, Tuple],
        messages: Sequence[SyslogMessage],
    ) -> LogwatchFordwardResult:
        if not method:
            method = str(cmk.utils.paths.omd_root / "tmp/run/mkeventd/eventsocket")
        elif isinstance(method, str) and method == "spool:":
            method += str(cmk.utils.paths.omd_root / "var/mkeventd/spool")

        if isinstance(method, tuple):
            return logwatch_forward_tcp(
                method,
                messages,
                logwatch_spool_path(self.hostname),
                self.hostname,
            )

        if not method.startswith("spool:"):
            return logwatch_forward_pipe(
                Path(method),
                messages,
            )

        return logwatch_forward_spool_directory(method, self.item, messages, self.hostname)


# write into local event pipe
# Important: When the event daemon is stopped, then the pipe
# is *not* existing! This prevents us from hanging in such
# situations. So we must make sure that we do not create a file
# instead of the pipe!
def logwatch_forward_pipe(
    path: Path,
    events: Sequence[SyslogMessage],
) -> LogwatchFordwardResult:
    if not events:
        return LogwatchFordwardResult()
    SyslogForwarderUnixSocket(path=path).forward(events)
    return LogwatchFordwardResult(num_forwarded=len(events))


# Spool the log messages to given spool directory.
# First write a file which is not read into ec, then
# perform the move to make the file visible for ec
def logwatch_forward_spool_directory(
    method: str,
    item: Optional[str],
    syslog_messages: Sequence[SyslogMessage],
    hostname: HostName,
) -> LogwatchFordwardResult:
    if not syslog_messages:
        return LogwatchFordwardResult()

    split_files = split_file_messages((message + "\n" for message in map(repr, syslog_messages)))
    for file_index, file in enumerate(split_files):
        spool_file = get_new_spool_file(method, item, file_index, hostname)
        with spool_file.open("w") as f:
            for message in file:
                f.write(message)
        spool_file.rename(spool_file.parent / spool_file.name[1:])

    return LogwatchFordwardResult(num_forwarded=len(syslog_messages))


def split_file_messages(file_messages: Generator[str, None, None]) -> list[list[str]]:
    result: list[list[str]] = [[]]
    curr_file_index = 0
    curr_file_size = 0
    for file_message in file_messages:
        if curr_file_size >= _MAX_SPOOL_SIZE:
            result.append([])
            curr_file_index += 1
            curr_file_size = 0
        result[curr_file_index].append(file_message)
        curr_file_size += len(file_message)

    return result


def get_new_spool_file(
    method: str,
    item: Optional[str],
    file_index: int,
    hostname: HostName,
) -> Path:
    spool_file = Path(
        method[6:],
        ".%s_%s%d_%d"
        % (
            hostname,
            (item.replace("/", "\\") + "_") if item else "",
            time.time(),
            file_index,
        ),
    )
    spool_file.parent.mkdir(parents=True, exist_ok=True)
    return spool_file


def logwatch_forward_tcp(
    method: Tuple,
    syslog_messages: Sequence[SyslogMessage],
    spool_path: Path,
    hostname: HostName,
) -> LogwatchFordwardResult:
    # Transform old format: (proto, address, port)
    if not isinstance(method[1], dict):
        method = (method[0], {"address": method[1], "port": method[2]})

    result = LogwatchFordwardResult()

    message_chunks = []

    if logwatch_shall_spool_messages(method):
        message_chunks += logwatch_load_spooled_messages(method, result, spool_path, hostname)

    # Add chunk of new messages (when there are new ones)
    if syslog_messages:
        message_chunks.append((time.time(), 0, list(map(repr, syslog_messages))))

    if not message_chunks:
        return result  # Nothing to process

    try:
        logwatch_forward_send_tcp(method, message_chunks, result)
    except Exception as exc:
        result.exception = exc

    if logwatch_shall_spool_messages(method):
        logwatch_spool_messages(message_chunks, result, spool_path)
    else:
        result.num_dropped = sum(len(c[2]) for c in message_chunks)

    return result


def logwatch_shall_spool_messages(method):
    return (
        isinstance(method, tuple)
        and method[0] == "tcp"
        and isinstance(method[1], dict)
        and "spool" in method[1]
    )


def logwatch_forward_send_tcp(
    method,
    message_chunks: Iterable[Tuple[float, int, List[str]]],
    result,
):
    protocol, method_params = method

    if protocol == "udp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    elif protocol == "tcp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        raise NotImplementedError()

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
def logwatch_spool_messages(
    message_chunks: Iterable[Tuple[float, int, List[str]]],
    result,
    spool_path: Path,
):
    spool_path.mkdir(parents=True, exist_ok=True)

    # Now write updated/new and delete emtpy spool files
    for time_spooled, num_already_spooled, message_chunk in message_chunks:
        spool_file_path = spool_path / ("spool.%0.2f" % time_spooled)

        if not message_chunk:
            # Cleanup empty spool files
            spool_file_path.unlink(missing_ok=True)
            continue

        try:
            # Partially processed chunks or the new one
            spool_file_path.write_text(repr(message_chunk))
            result.num_spooled += len(message_chunk)
        except Exception:
            if cmk.utils.debug.enabled():
                raise

            if num_already_spooled == 0:
                result.num_dropped += len(message_chunk)


def logwatch_load_spooled_messages(
    method: Tuple,
    result,
    spool_path: Path,
    hostname: HostName,
) -> List[Tuple[float, int, List[str]]]:
    spool_params = method[1]["spool"]

    try:
        spool_files = sorted(spool_path.iterdir())
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
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

        # Delete too old files by age
        if time_spooled < time.time() - spool_params["max_age"]:
            logwatch_spool_drop_messages(path, result)
            continue

    # Delete by size till half of target size has been deleted (oldest spool files first)
    if total_size > spool_params["max_size"]:
        target_size = int(spool_params["max_size"] / 2.0)

        for filename in spool_files:
            path = logwatch_spool_path(hostname) / filename

            total_size -= logwatch_spool_drop_messages(path, result)
            if target_size >= total_size:
                break  # cleaned up enough

    # Now process the remaining files
    for path in spool_files:
        time_spooled = float(path.name[6:])

        try:
            messages = ast.literal_eval(path.read_text())
        except IOError as exc:
            if exc.errno != errno.ENOENT:
                raise
            continue

        message_chunks.append((time_spooled, len(messages), messages))

    return message_chunks


def logwatch_spool_drop_messages(path: Path, result) -> int:
    messages = ast.literal_eval(path.read_text())
    result.num_dropped += len(messages)

    file_size = path.stat().st_size
    path.unlink()
    return file_size


def logwatch_spool_path(hostname: HostName) -> Path:
    return Path(cmk.utils.paths.var_dir, "logwatch_spool", hostname)
