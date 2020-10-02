#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
import io
import os
import socket
import time

from typing import Any, Counter, Dict, Iterable, List, Optional, Tuple, Union

import cmk.utils.debug
import cmk.utils.paths
import cmk.base.config  # from cmk.base.config import logwatch_rules will NOT work!
# import from legacy API until we come up with something better
from cmk.base.check_api import (
    get_effective_service_level,
    host_name,
    service_extra_conf,
)

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, Parameters
from .agent_based_api.v1 import Metric, register, Result, Service, State as state
from .utils import logwatch

ClusterSection = Dict[Optional[str], logwatch.Section]


def discover_group(
    params: List[Parameters],
    section: logwatch.Section,
) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(section, params, "groups")


def check_logwatch_ec(params: Parameters, section: logwatch.Section) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(None, params, {None: section})


def cluster_check_logwatch_ec(params: Parameters, section: ClusterSection) -> CheckResult:
    yield from check_logwatch_ec_common(None, params, section)


register.check_plugin(
    name="logwatch_ec",
    service_name="Log Forwarding",
    sections=["logwatch"],
    discovery_function=discover_group,
    discovery_default_parameters={},
    discovery_ruleset_name="logwatch_ec",
    discovery_ruleset_type="all",
    check_function=check_logwatch_ec,
    check_default_parameters={},
    check_ruleset_name="logwatch_ec",
    cluster_check_function=cluster_check_logwatch_ec,
)


def discover_single(
    params: List[Parameters],
    section: logwatch.Section,
) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(section, params, "single")


def check_logwatch_ec_single(
    item: str,
    params: Parameters,
    section: logwatch.Section,
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(item, params, {None: section})


def cluster_check_logwatch_ec_single(
    item: str,
    params: Parameters,
    section: ClusterSection,
) -> CheckResult:
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(item, params, section)


register.check_plugin(
    name="logwatch_ec_single",
    service_name="Log %s",
    sections=["logwatch"],
    discovery_function=discover_single,
    discovery_default_parameters={},
    discovery_ruleset_name="logwatch_ec",
    discovery_ruleset_type="all",
    check_function=check_logwatch_ec_single,
    check_default_parameters={},
    cluster_check_function=cluster_check_logwatch_ec_single,
)


# OK      -> priority 5 (notice)
# WARN    -> priority 4 (warning)
# CRIT    -> priority 2 (crit)
# context -> priority 6 (info)
# u = Uknown
def logwatch_to_prio(level: str) -> int:
    if level == 'W':
        return 4
    if level == 'C':
        return 2
    if level == 'O':
        return 5
    if level == '.':
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
    params: List[Parameters],
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
    for key in ["method", "facility", "monitor_logfilelist", "logwatch_reclassify"]:
        if key in merged_rules:
            single_log_params[key] = merged_rules[key]
    for log in forwarded_logs:
        single_log_params["expected_logfiles"] = [log]
        yield Service(item=log, parameters=single_log_params.copy())


def _filter_accumulated_lines(cluster_section: ClusterSection, item: str) -> Iterable[str]:
    # node info ignored (only used in regular logwatch check)
    for node_data in cluster_section.values():
        for line in node_data['logfiles'][item]['lines']:
            # skip context lines and ignore lines
            # skip context lines, ignore lines and empty lines
            if line[0] not in ['.', 'I'] and len(line) > 1:
                yield line


def check_logwatch_ec_common(
    item: Optional[str],
    params: Parameters,
    parsed: ClusterSection,
) -> CheckResult:
    yield from logwatch.errors(parsed)

    if item:
        # If this check has an item (logwatch.ec_single), only forward the information from this log
        if (not any(item in node_data['logfiles'] for node_data in parsed.values()) or
                not logwatch.ec_forwarding_enabled(params, item)):
            return
        used_logfiles = [item]
    else:
        # Filter logfiles if some should be excluded
        used_logfiles = [
            name for node_data in parsed.values() for name in node_data['logfiles']
            if logwatch.ec_forwarding_enabled(params, name)
        ]

    # Check if the number of expected files matches the actual one
    if params.get('monitor_logfilelist'):
        if 'expected_logfiles' not in params:
            yield Result(
                state=state.WARN,
                summary=("You enabled monitoring the list of forwarded logfiles. "
                         "You need to redo service discovery."),
            )
        else:
            expected = params['expected_logfiles']
            missing = [f for f in expected if f not in used_logfiles]
            if missing:
                yield Result(
                    state=state.WARN,
                    summary="Missing logfiles: %s" % (", ".join(missing)),
                )

            exceeding = [f for f in used_logfiles if f not in expected]
            if exceeding:
                yield Result(
                    state=state.WARN,
                    summary="Newly appeared logfiles: %s" % (", ".join(exceeding)),
                )

    # 3. create syslog message of each line
    # <128> Oct 24 10:44:27 Klappspaten /var/log/syslog: Oct 24 10:44:27 Klappspaten logger: asdasas
    # <facility+priority> timestamp hostname logfile: message
    facility = params.get('facility', 17) << 3  # default to "local1"
    messages = []
    cur_time = int(time.time())

    forwarded_logfiles = set([])

    # Keep track of reclassifed lines
    rclfd_total = 0
    rclfd_to_ignore = 0

    logfile_reclassify_settings: Dict[str, Any] = {}
    service_level = get_effective_service_level()

    def add_reclassify_settings(settings):
        if isinstance(settings, dict):
            logfile_reclassify_settings["reclassify_patterns"].extend(
                settings.get("reclassify_patterns", []))
            if "reclassify_states" in settings:
                logfile_reclassify_settings["reclassify_states"] = settings["reclassify_states"]
        else:  # legacy configuration
            logfile_reclassify_settings["reclassify_patterns"].extend(settings)

    for logfile in used_logfiles:
        lines = _filter_accumulated_lines(parsed, logfile)

        logfile_reclassify_settings["reclassify_patterns"] = []
        logfile_reclassify_settings["reclassify_states"] = {}

        # Determine logwatch patterns specifically for this logfile
        if params.get("logwatch_reclassify"):
            logfile_settings = service_extra_conf(
                host_name(),
                logfile,
                cmk.base.config.logwatch_rules,
            )
            for settings in logfile_settings:
                add_reclassify_settings(settings)

        for line in lines:
            rclfd_level = None
            if logfile_reclassify_settings:
                old_level, _text = line.split(" ", 1)
                level = logwatch.reclassify(Counter(), logfile_reclassify_settings, line[2:],
                                            old_level)
                if level != old_level:
                    rclfd_total += 1
                    rclfd_level = level
                    if level == "I":  # Ignored lines are not forwarded
                        rclfd_to_ignore += 1
                        continue

            msg = '<%d>' % (facility + logwatch_to_prio(rclfd_level or line[0]),)
            msg += '@%s;%d;; %s %s: %s' % (cur_time, service_level, host_name(), logfile, line[2:])

            messages.append(msg)
            forwarded_logfiles.add(logfile)

    try:
        if forwarded_logfiles:
            logfile_info = " from " + ",".join(forwarded_logfiles)
        else:
            logfile_info = ""

        result = logwatch_forward_messages(params.get("method"), item, messages)

        yield Result(
            state=state.OK,
            summary="Forwarded %d messages%s" % (result.num_forwarded, logfile_info),
        )
        yield Metric('messages', result.num_forwarded)

        exc_txt = " (%s)" % result.exception if result.exception else ""

        if result.num_spooled:
            yield Result(
                state=state.WARN,
                summary="Spooled %d messages%s" % (result.num_spooled, exc_txt),
            )

        if result.num_dropped:
            yield Result(
                state=state.CRIT,
                summary="Dropped %d messages%s" % (result.num_dropped, exc_txt),
            )

    except Exception as exc:
        if cmk.utils.debug.enabled():
            raise
        yield Result(
            state=state.CRIT,
            summary='Failed to forward messages (%s). Lost %d messages.' % (exc, len(messages)),
        )

    if rclfd_total:
        yield Result(
            state=state.OK,
            summary='Reclassified %d messages through logwatch patterns (%d to IGNORE)' %
            (rclfd_total, rclfd_to_ignore),
        )


class LogwatchFordwardResult:
    def __init__(self, num_forwarded=0, num_spooled=0, num_dropped=0, exception=None):
        self.num_forwarded = num_forwarded
        self.num_spooled = num_spooled
        self.num_dropped = num_dropped
        self.exception = exception


# send messages to event console
# a) local in same omd site
# b) local pipe
# c) remote via udp
# d) remote via tcp
def logwatch_forward_messages(
    method: Union[None, str, Tuple],
    item: Optional[str],
    messages: List[str],
) -> LogwatchFordwardResult:
    if not method:
        method = cmk.utils.paths.omd_root + "/tmp/run/mkeventd/eventsocket"
    elif isinstance(method, str) and method == 'spool:':
        method += cmk.utils.paths.omd_root + "/var/mkeventd/spool"

    if isinstance(method, tuple):
        return logwatch_forward_tcp(method, messages)

    if not method.startswith('spool:'):
        return logwatch_forward_pipe(method, messages)

    return logwatch_forward_spool_directory(method, item, messages)


# write into local event pipe
# Important: When the event daemon is stopped, then the pipe
# is *not* existing! This prevents us from hanging in such
# situations. So we must make sure that we do not create a file
# instead of the pipe!
def logwatch_forward_pipe(method, messages):
    if not messages:
        return LogwatchFordwardResult()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(method)
    sock.send(('\n'.join(messages) + '\n').encode("utf-8"))
    sock.close()

    return LogwatchFordwardResult(num_forwarded=len(messages))


# Spool the log messages to given spool directory.
# First write a file which is not read into ec, then
# perform the move to make the file visible for ec
def logwatch_forward_spool_directory(
    method: str,
    item: Optional[str],
    messages: List[str],
) -> LogwatchFordwardResult:
    if not messages:
        return LogwatchFordwardResult()

    spool_path = method[6:]
    file_name = '.%s_%s%d' % (host_name(), item and item.replace('/', '\\') + '_' or
                              '', time.time())
    os.makedirs(spool_path, exist_ok=True)

    io.open('%s/%s' % (spool_path, file_name), 'w', encoding="utf-8").write(
        ('\n'.join(messages) + '\n').encode("utf-8"))
    os.rename('%s/%s' % (spool_path, file_name), '%s/%s' % (spool_path, file_name[1:]))

    return LogwatchFordwardResult(num_forwarded=len(messages))


def logwatch_forward_tcp(method: Tuple, new_messages: List[str]) -> LogwatchFordwardResult:
    # Transform old format: (proto, address, port)
    if not isinstance(method[1], dict):
        method = (method[0], {"address": method[1], "port": method[2]})

    result = LogwatchFordwardResult()

    message_chunks = []

    if logwatch_shall_spool_messages(method):
        message_chunks += logwatch_load_spooled_messages(method, result)

    # Add chunk of new messages (when there are new ones)
    if new_messages:
        message_chunks.append((time.time(), 0, new_messages))

    if not message_chunks:
        return result  # Nothing to process

    try:
        logwatch_forward_send_tcp(method, message_chunks, result)
    except Exception as exc:
        result.exception = exc

    if logwatch_shall_spool_messages(method):
        logwatch_spool_messages(message_chunks, result)
    else:
        result.num_dropped = sum([len(c[2]) for c in message_chunks])

    return result


def logwatch_shall_spool_messages(method):
    return isinstance(method, tuple) and method[0] == "tcp" \
            and isinstance(method[1], dict) and "spool" in method[1]


def logwatch_forward_send_tcp(method, message_chunks, result):
    protocol, method_params = method

    if protocol == 'udp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    elif protocol == 'tcp':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        raise NotImplementedError()

    sock.connect((method_params["address"], method_params["port"]))

    try:
        for _time_spooled, _num_spooled, message_chunk in message_chunks:
            while message_chunk:
                try:
                    message = message_chunk[0]
                except IndexError:
                    break  # chunk complete

                sock.send(message.encode("utf-8") + "\n")
                message_chunk.pop(0)  # remove sent message
                result.num_forwarded += 1
    except Exception as exc:
        result.exception = exc
    finally:
        sock.close()


# a) Rewrite chunks that have been processed partially
# b) Write files for new chunk
def logwatch_spool_messages(message_chunks, result):
    path = logwatch_spool_path()

    os.makedirs(path, exist_ok=True)

    # Now write updated/new and delete emtpy spool files
    for time_spooled, num_already_spooled, message_chunk in message_chunks:
        spool_file_path = "%s/spool.%0.2f" % (path, time_spooled)

        if not message_chunk:
            # Cleanup empty spool files
            try:
                os.unlink(spool_file_path)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    raise
            continue

        try:
            # Partially processed chunks or the new one
            with io.open(spool_file_path, "w", encoding="utf-8") as handle:
                handle.write(repr(message_chunk))

            result.num_spooled += len(message_chunk)
        except Exception:
            if cmk.utils.debug.enabled():
                raise

            if num_already_spooled == 0:
                result.num_dropped += len(message_chunk)


def logwatch_load_spooled_messages(method, result):
    spool_params = method[1]["spool"]

    try:
        spool_files = sorted(os.listdir(logwatch_spool_path()))
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
        return []

    message_chunks = []

    total_size = 0
    for filename in spool_files:
        path = logwatch_spool_path() + "/" + filename

        # Delete unknown files
        if not filename.startswith("spool."):
            os.unlink(path)
            continue

        time_spooled = float(filename[6:])
        file_size = os.stat(path).st_size
        total_size += file_size

        # Delete fully processed files
        if file_size in [0, 2]:
            os.unlink(path)
            continue

        # Delete too old files by age
        if time_spooled < time.time() - spool_params["max_age"]:
            logwatch_spool_drop_messages(path, result)
            continue

    # Delete by size till half of target size has been deleted (oldest spool files first)
    if total_size > spool_params["max_size"]:
        target_size = int(spool_params["max_size"] / 2.0)

        for filename in spool_files:
            path = logwatch_spool_path() + "/" + filename

            total_size -= logwatch_spool_drop_messages(path, result)
            if target_size >= total_size:
                break  # cleaned up enough

    # Now process the remaining files
    for filename in spool_files:
        path = logwatch_spool_path() + "/" + filename
        time_spooled = float(filename[6:])

        try:
            messages = ast.literal_eval(io.open(path, encoding="utf-8").read())
        except IOError as exc:
            if exc.errno != errno.ENOENT:
                raise
            continue

        message_chunks.append((time_spooled, len(messages), messages))

    return message_chunks


def logwatch_spool_drop_messages(path, result):
    messages = ast.literal_eval(io.open(path, encoding="utf-8").read())
    result.num_dropped += len(messages)

    file_size = os.stat(path).st_size
    os.unlink(path)
    return file_size


def logwatch_spool_path():
    return cmk.utils.paths.var_dir + "/logwatch_spool/" + host_name()
