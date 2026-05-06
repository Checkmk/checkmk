#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plug-in is notorious for being an exception to just about every rule   #
#   or best practice that applies to check plug-in development.                         #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import time
from collections import defaultdict
from collections.abc import Container, Iterable, Mapping, MutableMapping, Sequence
from typing import Any, Literal

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
from cmk.ccc.hostaddress import HostName
from cmk.ec.forwarder import MessageForwarder
from cmk.ec.syslog import SyslogMessage
from cmk.logwatch.config import (
    CommonLogwatchEc,
    get_global_state,
    NEVER_DISCOVER_SERVICE_LABELS,
    ParameterLogwatchEc,
)

from . import commons as logwatch

CHECK_DEFAULT_PARAMETERS: logwatch.PreDictLogwatchEc = {
    "facility": 17,  # default to "local1"
    "method": "",  # local site
    "monitor_logfilelist": False,
    "monitor_logfile_access_state": 2,
    # These next three entries will be postprocessed by the backend.
    # Don't try this hack at home, we are trained professionals.
    "service_level": ("cmk_postprocessed", "service_level", None),
    "host_name": ("cmk_postprocessed", "host_name", None),
    "is_preview": ("cmk_postprocessed", "is_preview", None),
}


def discover_group(section: logwatch.Section, params: Mapping[str, str]) -> DiscoveryResult:
    yield from discover_logwatch_ec_common(
        section, get_global_state().logwatch_ec_all(params["host_name"]), "groups"
    )


def check_logwatch_ec(params: ParameterLogwatchEc, section: logwatch.Section) -> CheckResult:
    config = get_global_state()
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        None,
        params,
        {None: section},
        check_plugin_logwatch_ec,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(
            None,
            HostName(params["host_name"]),
            config.base_spool_path,
            config.omd_root,
            debug=config.debug,
        ),
    )


def cluster_check_logwatch_ec(
    params: ParameterLogwatchEc, section: Mapping[str, logwatch.Section | None]
) -> CheckResult:
    config = get_global_state()
    yield from check_logwatch_ec_common(
        None,
        params,
        {k: v for k, v in section.items() if v is not None},
        check_plugin_logwatch_ec,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(
            None,
            HostName(params["host_name"]),
            config.base_spool_path,
            config.omd_root,
            debug=config.debug,
        ),
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
        section, get_global_state().logwatch_ec_all(params["host_name"]), "single"
    )


def check_logwatch_ec_single(
    item: str,
    params: ParameterLogwatchEc,
    section: logwatch.Section,
) -> CheckResult:
    config = get_global_state()
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {None: section},
        check_plugin_logwatch_ec_single,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(
            item,
            HostName(params["host_name"]),
            config.base_spool_path,
            config.omd_root,
            debug=config.debug,
        ),
    )


def cluster_check_logwatch_ec_single(
    item: str,
    params: ParameterLogwatchEc,
    section: Mapping[str, logwatch.Section | None],
) -> CheckResult:
    config = get_global_state()
    # fall back to the cluster case with None as node name.
    yield from check_logwatch_ec_common(
        item,
        params,
        {k: v for k, v in section.items() if v is not None},
        check_plugin_logwatch_ec_single,
        value_store=get_value_store(),
        message_forwarder=MessageForwarder(
            item,
            HostName(params["host_name"]),
            config.base_spool_path,
            config.omd_root,
            debug=config.debug,
        ),
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
    forward_settings: Sequence[ParameterLogwatchEc],
) -> tuple[Literal["no", "single", "groups"], CommonLogwatchEc]:
    merged_rules: CommonLogwatchEc = {}
    for rule in forward_settings[-1::-1]:
        merged_rules.update(rule)

    if forward_settings and not merged_rules.get("activation", True):
        return "no", {}  # Configured "activation" to be False.

    if merged_rules.get("separate_checks", False):
        return "single", merged_rules
    return "groups", merged_rules


def discover_logwatch_ec_common(
    section: logwatch.Section,
    params: Sequence[ParameterLogwatchEc],
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
            labels=NEVER_DISCOVER_SERVICE_LABELS,
        )
        return

    single_log_params = CommonLogwatchEc()
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
            labels=NEVER_DISCOVER_SERVICE_LABELS,
        )


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
    params: ParameterLogwatchEc,
    parsed: logwatch.ClusterSection,
    plugin: CheckPlugin,
    *,
    value_store: MutableMapping[str, Any],
    message_forwarder: MessageForwarder,
) -> CheckResult:
    timestamp = time.time()
    yield from logwatch.check_errors(parsed)

    host_name = params["host_name"]
    is_preview = params["is_preview"]

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
        rules_for_this_file = get_global_state().logwatch_rules_all(
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
                SyslogMessage(
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

    logfile_info = (" from " + ", ".join(sorted(forwarded_logfiles))) if forwarded_logfiles else ""

    if is_preview:
        yield Result(
            state=State.OK,
            summary="Preview: %d messages would be forwarded%s"
            % (len(syslog_messages), logfile_info),
        )
    else:
        try:
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
            if message_forwarder.debug:
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
